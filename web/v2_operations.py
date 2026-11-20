"""Operations executed by V2 workers after consuming a correlated Redis request."""
import json
import re

from fastapi import HTTPException
from pydantic import ValidationError

import catalog
import explain
import garment_measurement as measurement
import listing_fit
import model_pair
import resale
import settings
import sizing
import team_bridge
import v2_store


def json_object(data):
    try:
        result = json.loads(data)
        if not isinstance(result, dict):
            raise ValueError()
        return result
    except (ValueError, UnicodeError, RecursionError):
        raise HTTPException(422, "요청의 JSON 형식을 확인해 주세요.") from None


def opaque_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{32}", value):
        raise HTTPException(422, "요청 식별자를 확인해 주세요.")
    return value


def db_operation(operation, data):
    if operation == "health":
        ok, _ = team_bridge.db_available()
        return {"version":"2", "mode":"db" if ok else settings.DATA_MODE, "db_connected":ok,
                "data_mode_setting":settings.DATA_MODE, "ai_configured":settings.ai_configured(),
                "db_error":"" if ok else "DB 연결을 확인해 주세요.", "worker":"db"}
    if operation == "search":
        q = data.get("q")
        if not isinstance(q, str) or not 1 <= len(q) <= 400:
            raise HTTPException(422, "검색할 모델명이나 품번을 입력해 주세요.")
        return resale.search(q)
    if operation == "chart":
        garment = data.get("garment_id")
        if type(garment) is not int:
            raise HTTPException(422, "상품 식별자를 확인해 주세요.")
        return resale.size_chart(garment)
    if operation == "recommend":
        return listing_fit.recommend_listing(listing_fit.ListingFitRequest.model_validate(data))
    if operation == "ease":
        return listing_fit.ease_sizes(listing_fit.EaseRequest.model_validate(data))
    if operation in ("save_listing", "listing_replay"):
        key = opaque_id(data.get("key"))
        card = v2_store.Listing.model_validate(data.get("card")).model_dump(mode="json", exclude_none=True)
        if operation == "listing_replay":
            return v2_store.listing_replay(key, card)
        return v2_store.save_listing(key, card)
    if operation == "get_listing":
        return v2_store.get_listing(opaque_id(data.get("id")))
    if operation == "legacy_products":
        return catalog.list_products()
    if operation == "legacy_resolve":
        parsed = catalog.parse_link(data.get("link", ""))
        return catalog.find_product(parsed["item_code"], parsed["region"]) if parsed["ok"] else parsed
    if operation == "legacy_fit":
        result = sizing.recommend(data)
        if result["ok"]:
            result["explanation"] = explain.explain(result)
        return result
    raise HTTPException(404, "요청한 데이터 작업을 찾을 수 없어요.")


def media_operation(operation, body, job_id):
    if operation in ("garment_catalog", "garment_catalog_sizes", "check_catalog_selection"):
        import team_catalog
        data = json_object(body)
        if operation == "garment_catalog":
            return team_catalog.list_garments()
        if operation == "garment_catalog_sizes":
            return team_catalog.list_sizes(data["garment_id"])
        return team_catalog.check_selection(data["garment_id"], data["size_id"])
    if operation == "pair_status":
        return {"configured": model_pair.configuration() is not None}
    if operation == "status":
        return measurement.status()
    if operation == "sample":
        return measurement.sample()
    if operation == "import":
        return measurement.parse_import(body)
    if operation == "get_model":
        asset = v2_store.capture(opaque_id(json_object(body).get("id")))
        if not asset or not asset["blob_name"]:
            raise HTTPException(404, "해당 매물의 3D 모델을 찾지 못했어요.")
        return measurement.read_model(asset["blob_name"])
    if operation == "measure":
        if len(body) > measurement.MAX_PHOTO_BYTES:
            raise HTTPException(413, "사진은 4 MB까지 전송할 수 있어요.")
        if not body.startswith(b"\xff\xd8\xff") or not body.endswith(b"\xff\xd9"):
            raise HTTPException(415, "JPEG 사진을 확인해 주세요.")
        key = opaque_id(job_id)
        previous = v2_store.capture(key)
        if previous:
            return json.loads(previous["result_json"])
        url = measurement.service_url()
        if not url:
            raise HTTPException(503, "촬영 측정 서버 연결을 기다리고 있어요.")
        result = measurement.request_measurement(url, body, key)
        blob_name = result.pop("model_blob", None)
        if blob_name:
            result["modelAsset"] = key
        v2_store.save_capture(key, result, blob_name)
        return result
    raise HTTPException(404, "요청한 촬영 작업을 찾을 수 없어요.")


def dispatch(lane, operation, body_bytes, job_hex_id):
    try:
        if lane == "pair" and operation == "generate_pair":
            data = json_object(body_bytes)
            inputs = model_pair.ModelPairRequest.model_validate(data.get("input"))
            return model_pair.generate_pair(inputs, data["subject"])
        if lane == "db":
            return db_operation(operation, json_object(body_bytes))
        if lane == "media":
            return media_operation(operation, body_bytes, job_hex_id)
    except ValidationError:
        raise HTTPException(422, "입력한 값 또는 매물 치수를 확인해 주세요.") from None
    raise HTTPException(404, "요청한 처리 서버를 찾을 수 없어요.")
