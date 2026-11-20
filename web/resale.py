"""중고 의류 태그와 팀 카탈로그 대조. 모델 확인 뒤 지역·사이즈별 옷 실측만 제공한다."""
import re
import unicodedata
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Query

import team_bridge
import settings
from team_bridge import _db

router = APIRouter(prefix="/api/resale")


@router.get("/preview-model")
def preview_model():
    url = settings.get("GARMENT_GLB_URL")
    # This URL goes directly to the browser. Restrict it to Azure public Blob endpoints.
    try:
        parts = urlsplit(url)
        if (parts.scheme == "https" and parts.hostname and
                re.fullmatch(r"[a-z0-9]{3,24}\.blob\.core\.windows\.net", parts.hostname) and
                parts.port in (None, 443) and parts.username is None and parts.password is None and
                parts.path.lower().endswith(".glb") and not parts.fragment):
            return {"source": "blob", "url": url}
    except ValueError:
        pass
    return {"source": "sample", "url": "/static/models/striped-tee.glb"}

# DB가 없을 때도 팀 db/sample/sample_data.sql과 같은 품번·사이즈·측정값을 사용한다.
SAMPLE = {"garment_id": 14, "item_code": "1848166", "brand_name": "COVERNAT",
          "garment_name": "에센셜 쿨 코튼 2-PACK 티셔츠 블랙", "category": "상의"}
SAMPLE_MEASURES = {"가슴단면": 55.0, "어깨너비": 51.0, "총장": 69.0, "소매길이": 21.5}


@router.get("/search")
def search(q: str = Query(min_length=1, max_length=400)):
    query = unicodedata.normalize("NFKC", q).strip().casefold()
    tokens = re.findall(r"[\w]+(?:[-./][\w]+)*", query)
    if not tokens:
        return {"items": []}
    mode = team_bridge.current_mode()
    if mode == "demo":
        name = SAMPLE["garment_name"].casefold()
        matches = (SAMPLE["item_code"] in tokens or query in name or name in query
                   or query == SAMPLE["brand_name"].casefold())
        return {"items": [SAMPLE] if matches else [], "mode": mode}

    # 품번은 출처마다 모양이 다르다. 같은 품번을 쓰는 상품도 각각 선택하게 한다.
    placeholders = ", ".join(["%s"] * len(tokens))
    items = _db.query(f"""
        SELECT g.garment_id, g.item_code, g.garment_name, g.category, b.brand_name
        FROM garment.garments g LEFT JOIN garment.brands b ON b.brand_id = g.brand_id
        WHERE LOWER(g.item_code) IN ({placeholders})
           OR LOCATE(%s, LOWER(g.garment_name)) > 0
           OR (CHAR_LENGTH(TRIM(g.garment_name)) >= 3 AND LOCATE(LOWER(g.garment_name), %s) > 0)
           OR LOWER(b.brand_name) = %s
        ORDER BY (LOWER(g.item_code) IN ({placeholders})) DESC, g.garment_id
        LIMIT 25
    """, (*tokens, query, query, query, *tokens))
    return {"items": items, "mode": mode}


@router.get("/garments/{garment_id}")
def size_chart(garment_id: int):
    mode = team_bridge.current_mode()
    if mode == "demo":
        if garment_id != SAMPLE["garment_id"]:
            raise HTTPException(404, "상품을 찾을 수 없어요.")
        return {"mode": mode, "sizes": [
            {"region": "KR", "label": size, "measures": SAMPLE_MEASURES if size == "M" else {}}
            for size in ("XS", "S", "M", "L", "XL", "XXL")
        ]}

    rows = _db.query("""
        SELECT s.size_id, s.region, s.size_label, m.value_cm,
               COALESCE(d.korean_name, m.measure_code) AS name
        FROM garment.sizes s
        LEFT JOIN garment.measures m ON m.size_id = s.size_id AND m.basis = 'garment'
        LEFT JOIN ref.measure_definitions d ON d.measure_code = m.measure_code
        WHERE s.garment_id = %s ORDER BY s.size_id, m.measure_code
    """, (garment_id,))
    sizes = {}
    for row in rows:
        size = sizes.setdefault(row["size_id"], {"region": row["region"], "label": row["size_label"], "measures": {}})
        if row["value_cm"] is not None:
            name = "어깨너비" if row["name"] == "어깨너비(옷)" else row["name"]
            size["measures"][name] = float(row["value_cm"])
    return {"mode": mode, "sizes": list(sizes.values())}
