"""The V2 media worker calls the garment VM and fetches its models from Blob storage."""
import json
import math
import re
import struct
from http.client import HTTPException as HTTPProtocolError
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request as UpstreamRequest, build_opener

from fastapi import HTTPException

import settings
from resale import SAMPLE, SAMPLE_MEASURES

MAX_PHOTO_BYTES = 4 * 1024 * 1024
MAX_RESULT_BYTES = 64 * 1024
MAX_MODEL_BYTES = 16 * 1024 * 1024

# Keys from ref.measure_definitions with basis='garment'. Body girths and projected
# silhouette dimensions have different definitions and are never forwarded as garment rows.
NAMES = {
    "body_length": "총장", "chest_width": "가슴단면", "garment_shoulder_width": "어깨너비",
    "sleeve_length": "소매길이", "waist_width": "허리단면", "hip_width": "엉덩이단면",
    "thigh_width": "허벅지단면", "knee_width": "무릎단면", "leg_opening": "밑단단면",
    "garment_inseam": "안쪽기장", "front_rise": "앞밑위", "back_rise": "뒷밑위",
}
CATEGORIES = {"상의": "상의·아우터", "아우터": "상의·아우터", "상의·아우터": "상의·아우터",
              "하의": "하의", "원피스": "원피스"}


def service_url():
    value = settings.get("GARMENT_MEASUREMENT_URL")
    try:
        parsed = urlsplit(value)
        local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if (not parsed.hostname or parsed.username or parsed.password or parsed.fragment
                or not (parsed.scheme == "https" or (local and parsed.scheme == "http"))):
            return None
        _ = parsed.port
    except ValueError:
        return None
    return value


def status():
    return {"configured": bool(service_url())}


def sample():
    return {"name": SAMPLE["garment_name"], "size": "KR · M", "category": "상의·아우터",
            "measureSource": "예시 카탈로그", "measures": SAMPLE_MEASURES}


class _NoRedirect(HTTPRedirectHandler):
    # A redirect must not silently change the destination of a seller's photo.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def parse_result(raw):
    failure = "측정 서버에서 의류 평면 치수(cm)를 확인할 수 없어요."
    if not isinstance(raw, dict) or raw.get("basis") != "garment" or raw.get("unit") != "cm":
        raise HTTPException(502, failure)
    values = raw.get("measurements")
    if not isinstance(values, dict):
        raise HTTPException(502, failure)
    measures = {}
    for code, name in NAMES.items():
        value = values.get(code)
        if value is None:
            continue
        if type(value) not in (int, float) or not 0 < value <= 400 or not math.isfinite(value):
            raise HTTPException(502, failure)
        measures[name] = value
    if not measures:
        raise HTTPException(422, "의류 치수를 얻지 못했어요. 옷 전체가 보이도록 다시 찍어 주세요.")
    category = raw.get("category")
    return {"name": "촬영한 옷", "size": "", "category": CATEGORIES.get(category, "") if isinstance(category, str) else "",
            "measureSource": "ML 추정", "measures": measures}


async def bounded_body(request, limit):
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > limit:
            raise HTTPException(413, "허용 파일 크기를 초과했어요.")
        data.extend(chunk)
    return bytes(data)


def parse_import(data):
    if len(data) > MAX_RESULT_BYTES:
        raise HTTPException(413, "측정 파일은 64 KB까지 열 수 있어요.")
    try:
        result = parse_result(json.loads(data))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise HTTPException(422, "측정 파일의 JSON 형식을 확인해 주세요.") from exc
    except HTTPException as exc:
        raise HTTPException(422, exc.detail) from exc
    return {**result, "name": "측정 파일의 옷", "measureSource": "ML 결과 파일"}


def request_measurement(url, photo, job_id=None):
    headers = {"Content-Type": "image/jpeg", "Accept": "application/json"}
    if job_id:
        headers["Idempotency-Key"] = job_id
    upstream = UpstreamRequest(url, data=photo, method="POST",
                               headers=headers)
    try:
        with build_opener(_NoRedirect()).open(upstream, timeout=35) as response:
            if response.status != 200:
                raise HTTPException(502, "측정 서버에서 완성된 결과를 받지 못했어요.")
            body = response.read(MAX_RESULT_BYTES + 1)
        if len(body) > MAX_RESULT_BYTES:
            raise HTTPException(502, "측정 서버 응답이 너무 커요.")
        raw = json.loads(body)
        result = parse_result(raw)
        if job_id and raw.get("model_blob") is not None:
            result["model_blob"] = validated_blob_name(raw["model_blob"])
        return result
    except HTTPError as exc:
        if exc.code in (400, 415, 422):
            raise HTTPException(422, "이 사진에서 치수를 얻지 못했어요. 다른 사진으로 시도해 주세요.") from exc
        raise HTTPException(502, "측정 서버가 요청을 처리하지 못했어요.") from exc
    except (URLError, OSError, HTTPProtocolError) as exc:
        raise HTTPException(503, "측정 서버에 연결할 수 없어요. 잠시 후 다시 시도해 주세요.") from exc
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(502, "측정 서버의 응답 형식을 확인해 주세요.") from exc


def validated_blob_name(value):
    if (not isinstance(value, str) or len(value) > 500 or not value.lower().endswith(".glb")
            or any(part in ("", ".", "..") for part in value.split("/"))
            or any(c in value for c in "\\%?#:") or not value.isprintable()):
        raise HTTPException(502, "측정 서버가 보낸 모델 파일명이 올바르지 않아요.")
    return value


def blob_url(name):
    # The VM supplies only a blob name. The worker owns the storage destination and SAS.
    validated_blob_name(name)
    try:
        parts = urlsplit(settings.get("GARMENT_BLOB_CONTAINER_URL"))
        hostname = parts.hostname or ""
        azure = parts.scheme == "https" and parts.port in (None, 443) and re.fullmatch(
            r"[a-z0-9]{3,24}\.blob\.core\.windows\.net", hostname)
        emulator = parts.scheme in ("http", "https") and hostname in ("127.0.0.1", "localhost", "::1")
        path = parts.path.rstrip("/")
        segments = path.split("/")[1:]
        if (not (azure or emulator) or parts.username is not None or parts.password is not None or parts.fragment
                or len(segments) not in ((1, 2) if emulator else (1,))
                or not all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", segment) for segment in segments)):
            raise ValueError()
    except ValueError:
        raise HTTPException(503, "3D 모델 저장소 연결을 기다리고 있어요.") from None
    return urlunsplit((parts.scheme, parts.netloc, path + "/" + quote(name, safe="/"), parts.query, ""))


def validate_glb(data):
    failure = HTTPException(502, "3D 모델 파일의 형식을 확인할 수 없어요.")
    if len(data) < 20 or struct.unpack_from("<4sII", data) != (b"glTF", 2, len(data)):
        raise failure
    offset = 12
    while offset < len(data):
        if offset + 8 > len(data):
            raise failure
        length, kind = struct.unpack_from("<I4s", data, offset)
        end = offset + 8 + length
        if length % 4 or end > len(data):
            raise failure
        if offset == 12:
            if kind != b"JSON":
                raise failure
            try:
                doc = json.loads(data[20:end])
                if not isinstance(doc, dict) or not isinstance(doc.get("asset"), dict) or doc["asset"].get("version") != "2.0":
                    raise ValueError()
                for entry in doc.get("buffers", []) + doc.get("images", []):
                    uri = entry.get("uri")
                    if uri is not None and (not isinstance(uri, str) or not uri.startswith("data:")):
                        raise ValueError()
            except (ValueError, TypeError, AttributeError, UnicodeError, RecursionError):
                raise failure from None
        offset = end
    return data


def read_model(blob_name):
    req = UpstreamRequest(blob_url(blob_name), headers={"Accept":"model/gltf-binary"})
    try:
        with build_opener(_NoRedirect()).open(req, timeout=20) as response:
            if response.status != 200:
                raise HTTPException(502, "모델 저장소가 파일을 반환하지 않았어요.")
            data = response.read(MAX_MODEL_BYTES + 1)
        if len(data) > MAX_MODEL_BYTES:
            raise HTTPException(502, "이 모델은 16 MB를 초과해 열 수 없어요.")
        return validate_glb(data)
    except HTTPError as exc:
        if exc.code == 404:
            raise HTTPException(404, "저장소에서 모델을 찾지 못했어요.") from None
        raise HTTPException(502, "모델 저장소에서 파일을 받을 수 없어요.") from None
    except (URLError, OSError, HTTPProtocolError):
        raise HTTPException(503, "모델 저장소에 연결할 수 없어요.") from None
