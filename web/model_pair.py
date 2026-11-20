"""Generate the body first, then drape the DB-sized garment against that body."""
import base64
import binascii
from datetime import datetime, timezone
from hashlib import sha256
from http.client import HTTPException as HTTPProtocolError
from ipaddress import ip_address, ip_network
import json
import re
from typing import Literal
from urllib.error import HTTPError, URLError
from math import isfinite
from urllib.parse import parse_qsl, urlsplit
from urllib.request import Request, build_opener

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

import ease_rules
import garment_measurement
import settings
from team_bridge import team_check
from v2_bus import pair_vm_timeout
import v2_store

MAX_REPLY = 64 * 1024
MAX_PHOTO_BYTES = 3 * 1024 * 1024
MAX_PHOTO_B64 = 4 * ((MAX_PHOTO_BYTES + 2) // 3)
PRIVATE_NETWORKS = tuple(ip_network(cidr) for cidr in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7"))
SIDE_NAMES = {"body":"신체", "garment":"의류"}
# 의류 서버 /fit (ease_check) 에 보내는 신체 둘레. 판정 기준값은 ease_check 한 곳에서만 관리한다.
FIT_GIRTHS = ("chest_girth_cm", "waist_girth_cm", "hip_girth_cm")
FIT_VERDICTS = {"FIT", "NO_FIT", "UNDETERMINED"}
FIT_PART_STATUSES = {"OK", "TOO_TIGHT", "TOO_LOOSE", None}
FIT_TIMEOUT_SECONDS = 20


class BodyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    height_cm: float = Field(ge=team_check.HEIGHT_MIN, le=team_check.HEIGHT_MAX, strict=True)
    weight_kg: float = Field(ge=team_check.WEIGHT_MIN, le=team_check.WEIGHT_MAX, strict=True)
    photo_b64: str = Field(min_length=4, max_length=MAX_PHOTO_B64, repr=False)
    photo_mime: Literal["image/jpeg", "image/png"]

    def photo_bytes(self):
        return base64.b64decode(self.photo_b64, validate=True)

    @model_validator(mode="after")
    def validate_photo(self):
        try:
            data = self.photo_bytes()
        except (binascii.Error, ValueError) as exc:
            raise ValueError("사진 인코딩을 확인해 주세요.") from exc
        signature = b"\xff\xd8\xff" if self.photo_mime == "image/jpeg" else b"\x89PNG\r\n\x1a\n"
        if len(data) > MAX_PHOTO_BYTES or not data.startswith(signature):
            raise ValueError("3 MiB 이하의 JPEG 또는 PNG 사진이 필요해요.")
        # The avatar API verifies photos and downsizes large inputs to at most 16 MP.
        return self


class ListingReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    listing_id: v2_store.OpaqueID


class FitTarget(BaseModel):
    """판정할 상품과 구매자가 고른 사이즈. 의류 서버 /fit 이 item_code 로 실측을 조회한다."""
    model_config = ConfigDict(extra="forbid")
    item_code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    size_label: str = Field(min_length=1, max_length=40)


class ModelPairRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # body 를 빼면 의류 모델만 만든다 (사이즈를 바꿀 때 그 사이즈의 의류 GLB 만 다시 받기).
    body: BodyInput | None = None
    garment: ListingReference | v2_store.CatalogSelection
    fit: FitTarget | None = None
    # body 없이 옷만 받을 때, 이미 만든 신체 모델에 맞춰 옷을 시뮬레이션한다.
    body_model_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


def checked_url(value):
    if not isinstance(value, str) or not value or len(value) > 8192 or "\\" in value or "#" in value:
        raise ValueError("Invalid URL")
    if not value.isprintable() or any(char.isspace() for char in value):
        raise ValueError("Invalid URL characters")
    url = urlsplit(value)
    if not url.hostname or url.username is not None or url.password is not None:
        raise ValueError("Invalid authority")
    _ = url.port
    return url


def local_host(host):
    return host in {"localhost", "127.0.0.1", "::1"}


def vm_url(value):
    url = checked_url(value)
    if url.scheme == "https" or url.scheme == "http" and local_host(url.hostname):
        return value
    if url.scheme == "http":
        addr = ip_address(url.hostname)
        if any(addr in network for network in PRIVATE_NETWORKS):
            return value
    raise ValueError("Use an HTTPS or a private VM address")


def blob_base(value):
    url = checked_url(value)
    azure = url.scheme == "https" and url.port in (None, 443) and re.fullmatch(
        r"[a-z0-9]{3,24}\.blob\.core\.windows\.net", url.hostname)
    local = url.scheme in {"http", "https"} and local_host(url.hostname)
    segments = url.path.rstrip("/").split("/")[1:]
    if (not (azure or local) or url.query or len(segments) not in ((1, 2) if local else (1,))
            or not all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", s) for s in segments)):
        raise ValueError("Invalid Blob base")
    return url


def configuration():
    try:
        endpoints = {}
        for side in SIDE_NAMES:
            vm = vm_url(settings.get(side.upper() + "_MODEL_VM_URL"))
            base = blob_base(settings.get(side.upper() + "_MODEL_BLOB_BASE"))
            endpoints[side] = (vm, base)
        return endpoints
    except ValueError:
        return None


def origin(parsed):
    return parsed.scheme, parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)


def check_read_sas(query):
    entries = parse_qsl(query, keep_blank_values=True, strict_parsing=True, max_num_fields=32)
    params = dict(entries)
    allowed = {"sp","sr","sig","se","st","sv","spr","sip","skoid","sktid","skt","ske","sks","skv",
               "saoid","suoid","scid","ses","rscc","rscd","rsce","rscl","rsct"}
    if (len(entries) != len(params) or params.get("sp") != "r" or params.get("sr") != "b"
            or not params.get("sig") or params.keys() - allowed):
        raise ValueError("Not a read-only blob SAS")
    expiry = datetime.fromisoformat(params.get("se", "").replace("Z", "+00:00"))
    if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
        raise ValueError("Expired or invalid blob SAS")


def checked_asset(value, base, relative):
    target = checked_url(value)
    if origin(target) != origin(base) or target.path != base.path.rstrip("/") + "/" + relative:
        raise ValueError("Unexpected Blob asset")
    if target.query:
        check_read_sas(target.query)
    elif not local_host(target.hostname):
        raise ValueError("Missing private Blob read link")
    return value


def garment_selection(garment):
    if isinstance(garment, v2_store.CatalogSelection):
        return garment
    saved = v2_store.get_listing(garment.listing_id)
    try:
        return v2_store.CatalogSelection.model_validate(saved.get("catalogSelection"))
    except ValidationError:
        raise HTTPException(422, "판매자가 3D 상품과 사이즈를 연결한 매물이 필요해요.") from None


def ready_model(side, receipt, base, subject):
    preview = (isinstance(receipt, dict) and side == 'garment' and
               receipt.get('status') == 'error' and receipt.get('preview_available') is True)
    if not isinstance(receipt, dict) or receipt.get("status") != "ready" and not preview:
        raise ValueError("Expected completed VM receipt")
    digest = receipt.get("model_id")
    urls = receipt.get("urls")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest) or not isinstance(urls, dict):
        raise ValueError("Invalid model digest or links")
    directory = f"v2/garments/{digest}"
    files = {"glb_url":"model.glb", "anchors_url":"anchors.json"}
    if side == "body":
        owner = sha256(subject.encode()).hexdigest()
        directory = f"v2/avatars/{owner}/{digest}"
        if "measurements.json" in urls:
            files["measurements_url"] = "measurements.json"
    result = {"status":"ready", "model_id":digest}
    if preview:
        reasons = receipt.get('failure_reasons')
        if not isinstance(reasons, list) or not reasons or any(
                reason not in ('stretch_exceeded', 'unsettled', 'body_penetration',
                    'initial_intersection','simulation_timeout','simulation_diverged',
                    'non_finite_simulation','simulation_interrupted','simulation_incomplete',
                    'frame_timeout','pushout_rejected','collision_region_exited',
                    'compression_exceeded','invalid_rest_mesh','invalid_cloth_mesh',
                    'validation_incomplete','self_collision_setup_failed','sam_sizing_failed') for reason in reasons):
            raise ValueError('Invalid failed simulation report')
        result.update(status='error', preview_available=True, failure_reasons=reasons,
                      message='착장 시뮬레이션 실패 · 실패한 옷의 마지막 모습을 표시해요.')
    for field, filename in files.items():
        result[field] = checked_asset(urls.get(filename), base, f"{directory}/{filename}")
    return result


def generate(side, inputs, endpoint, subject):
    vm, base = endpoint
    message = SIDE_NAMES[side] + " 모델을 준비하지 못했어요. 다시 시도해 주세요."
    headers = {"Accept":"application/json", "X-FitMe-Subject":subject}
    if isinstance(inputs, BodyInput):
        data = inputs.photo_bytes()
        headers.update({"Content-Type":inputs.photo_mime, "height-cm":str(inputs.height_cm),
                        "weight-kg":str(inputs.weight_kg)})
    else:
        data = json.dumps(inputs if isinstance(inputs, dict) else inputs.model_dump()).encode()
        headers["Content-Type"] = "application/json"
    try:
        post = Request(vm, data=data, method="POST", headers=headers)
        with build_opener(garment_measurement._NoRedirect()).open(post, timeout=pair_vm_timeout()) as response:
            if response.status != 200:
                raise ValueError("Expected completed response")
            raw = response.read(MAX_REPLY + 1)
        if len(raw) > MAX_REPLY:
            raise ValueError("VM receipt too large")
        return ready_model(side, json.loads(raw), base, subject)
    except HTTPError as exc:
        if exc.code == 429:
            message = SIDE_NAMES[side] + " 모델 서버가 처리 중이에요. 잠시 뒤 다시 시도해 주세요."
        elif side == "garment" and exc.code in (404, 422):
            message = "선택한 상품·사이즈와 템플릿을 확인하고 다시 시도해 주세요. 착장 시뮬레이션이 완료되지 않았어요."
        elif side == "body" and exc.code in (413, 422):
            message = "한 사람의 전신이 보이는 JPEG·PNG 사진과 입력값을 확인해 주세요."
            if exc.code==422:
                # Forward only recognized photo codes, never upstream exception text.
                try:
                    raw=exc.read(4097)
                    payload=json.loads(raw) if len(raw)<=4096 else None
                    detail=payload.get('detail') if isinstance(payload,dict) else None
                    code=detail.get('code') if isinstance(detail,dict) else None
                except (ValueError,OSError,HTTPProtocolError,RecursionError):
                    code=None
                if code=='full_body_required':
                    return {'status':'error','error_code':code,
                        'message':'머리부터 양발과 양손이 사진 안에 모두 보이도록 다시 촬영해 주세요.'}
                if code=='single_person_required':
                    return {'status':'error','error_code':code,
                        'message':'한 사람의 머리부터 양발까지 모두 보이는 사진을 촬영해 주세요.'}
    except (ValueError, URLError, OSError, HTTPProtocolError, RecursionError):
        pass
    # Upstream details may include signed links or image data.
    return {"status":"error", "message":message}


def fit_url():
    """GARMENT_FIT_URL 이 있으면 그 주소, 없으면 의류 VM 과 같은 서버의 /fit (예: http://10.4.2.5:8002/fit)."""
    explicit = settings.get("GARMENT_FIT_URL")
    if explicit:
        return vm_url(explicit)
    vm = checked_url(vm_url(settings.get("GARMENT_MODEL_VM_URL")))
    return f"{vm.scheme}://{vm.netloc}/fit"


def read_reply(request, timeout):
    with build_opener(garment_measurement._NoRedirect()).open(request, timeout=timeout) as response:
        if response.status != 200:
            raise ValueError("Expected a completed response")
        raw = response.read(MAX_REPLY + 1)
    if len(raw) > MAX_REPLY:
        raise ValueError("Reply too large")
    return json.loads(raw)


def body_girths(body):
    """신체 VM 이 함께 올린 measurements.json 에서 둘레 3개를 꺼낸다 (target 우선, 없으면 SAM measured)."""
    doc = read_reply(Request(body["measurements_url"], headers={"Accept":"application/json"}), FIT_TIMEOUT_SECONDS)
    values = doc.get("measurements", doc) if isinstance(doc, dict) else {}
    girths = {}
    for key in FIT_GIRTHS:
        value = values.get(key) if isinstance(values, dict) else None
        if isinstance(value, dict):
            # ML 예측값(target)이 있으면 그것을, 비어 있으면 SAM 메시에서 잰 값(measured)을 쓴다.
            value = value.get("target") if value.get("target") is not None else value.get("measured")
        if isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value):
            girths[key] = float(value)
    return girths


def undetermined(reason):
    return ease_rules.undetermined(reason)


def judge_fit(target, body, subject):
    """신체 결과를 받은 뒤 의류 서버 /fit 으로 판정한다. /fit 이 실패하면 None (3D 는 그대로, 판정만 빠짐)."""
    if not isinstance(body, dict) or body.get("status") != "ready":
        return undetermined("신체 측정에 실패했습니다.")
    if not body.get("measurements_url"):
        return undetermined("신체 둘레를 받지 못했습니다.")
    try:
        girths = body_girths(body)
    except (ValueError, URLError, OSError, HTTPProtocolError, RecursionError):
        return undetermined("신체 둘레를 받지 못했습니다.")
    try:
        # 의류 서버 /fit 은 이 다섯 키만 받는다. 둘레가 없으면 null 로 보낸다(서버의 ease_check 가 UNDETERMINED 로 판정).
        payload = json.dumps({"item_code":target.item_code, "size_label":target.size_label,
                              **{key:girths.get(key) for key in FIT_GIRTHS}}).encode()
        reply = read_reply(Request(fit_url(), data=payload, method="POST", headers={
            "Content-Type":"application/json", "Accept":"application/json", "X-FitMe-Subject":subject}), FIT_TIMEOUT_SECONDS)
        # ease_check.check_all_sizes 결과를 화면에 필요한 값만 남겨 그대로 전달한다.
        selected = reply.get("selected") if isinstance(reply.get("selected"), dict) else reply
        verdict, message = selected.get("verdict"), selected.get("message_ko")
        if verdict not in FIT_VERDICTS or not isinstance(message, str) or not 0 < len(message) <= 500:
            raise ValueError("Unexpected /fit reply")
        parts = [{"part":part.get("part"), "status":part.get("status")} for part in selected.get("parts") or []
                 if isinstance(part, dict) and part.get("status") in FIT_PART_STATUSES][:8]
        recommended = reply.get("recommended_size")
        sizes = [{"size_label":item["size_label"], "verdict":item["verdict"]}
                 for item in reply.get("all_sizes") or []
                 if isinstance(item, dict) and isinstance(item.get("size_label"), str) and item.get("verdict") in FIT_VERDICTS]
        rules = reply.get("rules_version")
        return {"selected":{"verdict":verdict, "message_ko":message, "size_label":target.size_label, "parts":parts},
                "recommended_size":recommended if isinstance(recommended, str) and len(recommended) <= 40 else None,
                "all_sizes":sizes[:64], "rules_version":rules if isinstance(rules, str) and len(rules) <= 60 else None}
    except (ValueError, AttributeError, TypeError, KeyError, URLError, OSError, HTTPProtocolError, RecursionError):
        return None


def generate_pair(request, subject):
    endpoints = configuration()
    if not endpoints:
        raise HTTPException(503, "신체·의류 모델 서버 연결을 기다리고 있어요.")
    if (not isinstance(subject, str) or not subject.strip() or len(subject) > 255
            or not subject.isascii() or not subject.isprintable()):
        raise HTTPException(401, "3D 모델을 요청할 사용자 정보를 확인해 주세요.")
    selection = garment_selection(request.garment)
    if request.body is None:
        # 사이즈만 바꿀 때: 신체는 다시 만들지 않고, 이미 만든 신체(body_model_id)에 맞춰 옷만 시뮬레이션한다.
        payload = selection.model_dump()
        if request.body_model_id:
            payload["body_model_id"] = request.body_model_id
        return {"garment":generate("garment", payload, endpoints["garment"], subject)}
    # 옷 시뮬레이션은 실제 신체 GLB 가 필요하므로 신체를 먼저 만들고, 그 신체로 의류를 만든다.
    body = generate("body", request.body, endpoints["body"], subject)
    result = {"body":body}
    if request.fit:
        result["fit"] = judge_fit(request.fit, body, subject)
    if body["status"] != "ready":
        result["garment"] = {"status":"error", "message":"충돌 계산에 사용할 신체 모델을 생성하지 못해 의류를 준비하지 못했어요."}
        return result
    payload = {**selection.model_dump(), "body_model_id":body["model_id"]}
    result["garment"] = generate("garment", payload, endpoints["garment"], subject)
    return result
