# 목적: 상품 찾기 — 유니클로 링크에서 품번 꺼내기 → DB(또는 데모)에서 상품·사이즈표 조회
# FigJam "04 / AZURE LOGIC" 의 01 링크 입력 · 02 상품 확인 단계
import re
from urllib.parse import urlparse

import demo_data
import team_bridge
from team_bridge import team_rec, team_est, _db

# 유니클로 품번 모양: E + 숫자 6개 + - + 숫자 3개 (예: E422992-000). 링크 안 어디에 있어도 찾음
CODE_PATTERN = re.compile(r"(E?\d{6}-\d{3})", re.IGNORECASE)
REGIONS = {"kr": "KR", "us": "US", "jp": "JP"}


# 목적: 사용자가 붙여넣은 글자 → {"ok", "item_code", "region", "error"}
def parse_link(text):
    text = (text or "").strip()
    if text == "":
        return {"ok": False, "error": "유니클로 상품 링크를 붙여넣어 주세요."}
    region = "KR"
    if text.lower().startswith("http"):
        parsed = urlparse(text)
        if "uniqlo.com" not in parsed.netloc.lower():
            return {"ok": False, "error": "유니클로 상품 링크가 아니에요. uniqlo.com 주소인지 확인해 주세요."}
        parts = [p.lower() for p in parsed.path.split("/") if p]
        if len(parts) > 0 and parts[0] in REGIONS:
            region = REGIONS[parts[0]]
    match = CODE_PATTERN.search(text)
    if match is None:
        return {"ok": False, "error": "링크에서 품번(예: E422992-000)을 찾지 못했어요. 상품 상세 페이지 링크인지 확인해 주세요."}
    code = match.group(1).upper()
    if not code.startswith("E"):
        code = "E" + code
    return {"ok": True, "item_code": code, "region": region}


# --- DB 모드: 팀 테이블 garment.garments / garment.sizes / garment.measures ---------------------

def _db_find(item_code):
    rows = _db.query("""
        SELECT g.garment_id, g.source_name, g.item_code, g.garment_name, g.category, g.target_gender,
               b.brand_name
        FROM garment.garments AS g
        LEFT JOIN garment.brands AS b ON b.brand_id = g.brand_id
        WHERE g.item_code = %s
        ORDER BY g.garment_id
        LIMIT 1
    """, (item_code,))
    if len(rows) == 0:
        return None
    return rows[0]


# 목적: 이 상품에 사이즈가 등록된 지역 목록 (요청한 지역이 없으면 다른 지역으로 대신)
def _db_regions(garment_id):
    rows = _db.query("SELECT DISTINCT region FROM garment.sizes WHERE garment_id = %s ORDER BY region", (garment_id,))
    return [r["region"] for r in rows]


# 목적: 팀 _추천.py 의 size_rows + group_by_size 로 사이즈표 읽기 (팀 추천 코드와 완전히 같은 모양)
def _db_sizes(source_name, item_code, region):
    grouped = team_rec.group_by_size(team_rec.size_rows(source_name, item_code, region))
    sizes = []
    for size in grouped:
        sizes.append({
            "size_label": size["size_label"],
            "garment": {code: float(v) for code, v in size["garment"].items()},
            "body_range": {code: [lo, hi] for code, (lo, hi) in size["body"].items()},
        })
    return sizes


def _db_product(item_code, region):
    row = _db_find(item_code)
    if row is None:
        return None
    regions = _db_regions(row["garment_id"])
    if region not in regions and len(regions) > 0:
        region = regions[0]
    sizes = _db_sizes(row["source_name"], row["item_code"], region)
    return {
        "item_code": row["item_code"], "garment_name": row["garment_name"],
        "brand_name": row["brand_name"] or "-", "category": row["category"],
        "target_gender": row["target_gender"], "source_name": row["source_name"],
        "region": region, "regions": regions, "sizes": sizes,
    }


# --- 데모 모드 ---------------------------------------------------------------------------------

def _demo_product(item_code):
    for product in demo_data.PRODUCTS:
        if product["item_code"] == item_code:
            copy = dict(product)
            copy["regions"] = [product["region"]]
            return copy
    return None


# --- 화면이 부르는 함수 ---------------------------------------------------------------------------

# 목적: 품번 → 상품 정보 + 사이즈표 + 추천 가능 여부
def find_product(item_code, region="KR"):
    mode = team_bridge.current_mode()
    if mode == "db":
        product = _db_product(item_code, region)
    else:
        product = _demo_product(item_code)
    if product is None:
        return {"ok": False, "mode": mode, "error": "등록된 상품 중에서 찾지 못했어요. 다른 링크나 사진으로 다시 찾아 주세요."}

    measured = [s["size_label"] for s in product["sizes"] if len(s["garment"]) > 0]
    missing = [s["size_label"] for s in product["sizes"] if len(s["garment"]) == 0]
    product["measured_sizes"] = measured
    product["missing_sizes"] = missing
    product["can_recommend"] = len(measured) > 0     # FigJam: 필수 실측 확보 전에는 추천 보류
    product["product_url"] = "https://www.uniqlo.com/kr/ko/products/" + product["item_code"]
    return {"ok": True, "mode": mode, "product": product}


# 목적: 사진 검색 후보로 보여 줄 상품 목록 (Azure AI Search 연결 전 임시: 등록 상품 전체)
def list_products():
    mode = team_bridge.current_mode()
    if mode == "db":
        rows = _db.query("""
            SELECT g.item_code, g.garment_name, g.target_gender, b.brand_name,
                   COUNT(DISTINCT gm.size_id) AS measured_sizes
            FROM garment.garments AS g
            JOIN garment.brands AS b ON b.brand_id = g.brand_id
            LEFT JOIN garment.sizes AS s ON s.garment_id = g.garment_id
            LEFT JOIN garment.measures AS gm ON gm.size_id = s.size_id AND gm.basis = 'garment'
            WHERE b.brand_name = 'UNIQLO'
            GROUP BY g.item_code, g.garment_name, g.target_gender, b.brand_name
            ORDER BY measured_sizes DESC, g.item_code
        """)
        items = [{"item_code": r["item_code"], "garment_name": r["garment_name"], "brand_name": r["brand_name"],
                  "target_gender": r["target_gender"], "measured_sizes": int(r["measured_sizes"])} for r in rows]
    else:
        items = [{"item_code": p["item_code"], "garment_name": p["garment_name"], "brand_name": p["brand_name"],
                  "target_gender": p["target_gender"], "measured_sizes": len(p["sizes"])} for p in demo_data.PRODUCTS]
    return {"ok": True, "mode": mode, "items": items}


# 목적: 치수 코드 → 한글 이름 (DB 의 ref.measure_definitions, 없으면 데모 사전)
def measure_names():
    if team_bridge.current_mode() == "db":
        try:
            return team_est.korean_names()
        except Exception:
            pass
    return dict(demo_data.MEASURE_NAMES)
