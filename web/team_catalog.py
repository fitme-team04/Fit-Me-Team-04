"""Read catalog IDs from the same garment VM that renders a buyer's selection."""
import json
from http.client import HTTPException as ProtocolError
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, build_opener

from fastapi import HTTPException

import settings
from garment_measurement import _NoRedirect
from model_pair import vm_url


def valid_id(value):
    return type(value) is int and 0 < value <= 2_147_483_647


def catalog_rows(suffix, id_field, labels):
    try:
        base = urlsplit(vm_url(settings.get("GARMENT_MODEL_VM_URL")))
    except (TypeError, ValueError):
        raise HTTPException(503, "3D 의류 카탈로그 연결을 기다리고 있어요.") from None
    path = base.path.rstrip("/") + suffix
    url = urlunsplit((base.scheme, base.netloc, path, base.query, ""))
    req = Request(url, headers={"Accept": "application/json"})
    try:
        with build_opener(_NoRedirect()).open(req, timeout=5) as response:
            if response.status != 200:
                raise HTTPException(502, "3D 의류 목록을 읽지 못했어요.")
            data = response.read(1_048_577)
        if len(data) > 1_048_576:
            raise ValueError("Oversize catalog")
        rows = json.loads(data)
        if not isinstance(rows, list):
            raise ValueError("Invalid catalog")
        seen = set()
        items = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Invalid catalog row")
            key = row.get(id_field)
            if not valid_id(key) or key in seen:
                raise ValueError("Invalid catalog identifier")
            seen.add(key)
            item = {id_field: key}
            for field in labels:
                value = row[field]
                if value is None:
                    value = ""
                if not isinstance(value, str) or len(value) > 500:
                    raise ValueError("Invalid catalog label")
                item[field] = value
            items.append(item)
    except (HTTPError, URLError, OSError, ProtocolError):
        raise HTTPException(503, "3D 의류 카탈로그에 연결하지 못했어요.") from None
    except (KeyError, ValueError, UnicodeError, RecursionError):
        raise HTTPException(502, "3D 의류 카탈로그 응답을 확인해 주세요.") from None
    return {"items": items}


def list_garments():
    return catalog_rows("", "garment_id", ("item_code", "garment_name"))


def list_sizes(garment_id):
    if not valid_id(garment_id):
        raise HTTPException(422, "상품을 다시 선택해 주세요.")
    return catalog_rows(f"/{garment_id}/sizes", "size_id", ("size_label", "region"))


def check_selection(garment_id, size_id):
    if not valid_id(size_id) or not any(item["size_id"] == size_id for item in list_sizes(garment_id)["items"]):
        raise HTTPException(422, "이 상품에 등록된 사이즈를 선택해 주세요.")
    return {"ok": True}
