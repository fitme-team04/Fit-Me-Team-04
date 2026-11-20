# 목적: 옷(상품) 목록 보기 — 전체(앞 몇 개), 출처(source_name)별, 출처 + 상품번호로 한 벌 찾기
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 기본 — 표 1개(garment.garments) SELECT + WHERE·ORDER BY·LIMIT
# 출력: 옷 전체 표 14행(id·출처·상품번호·이름·종류·성별), 무신사 출처 옷 1행, uniqlo E422992-000 한 벌 dict 한 줄
# 실행: .venv/bin/python db/예시_코드/공통/옷/1_기본/01_옷_목록.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 옷 목록 (앞 limit 개)
def garments(limit=20):
    sql = """
        SELECT g.garment_id, g.brand_id, g.source_name, g.item_code, g.garment_name,
               g.category, g.target_gender
        FROM garment.garments AS g
        ORDER BY g.garment_id
        LIMIT %s
    """
    return query(sql, (limit,))


# 목적: 출처(uniqlo_site / musinsa_ml_project / kobo_garment_measurements ...) 하나의 옷
def garments_by_source(source_name="musinsa_ml_project"):
    sql = """
        SELECT g.garment_id, g.item_code, g.garment_name, g.category, g.target_gender
        FROM garment.garments AS g
        WHERE g.source_name = %s
        ORDER BY g.garment_id
    """
    return query(sql, (source_name,))


# 목적: 출처 + 상품번호로 옷 한 벌 (UNIQUE 키라 0 또는 1행, 없으면 None)
def garment_by_code(source_name="uniqlo_site", item_code="E422992-000"):
    sql = """
        SELECT g.garment_id, g.brand_id, g.garment_name, g.category, g.target_gender, g.fit
        FROM garment.garments AS g
        WHERE g.source_name = %s
          AND g.item_code = %s
    """
    rows = query(sql, (source_name, item_code))
    if len(rows) == 0:
        return None
    return rows[0]


if __name__ == "__main__":
    show("garment.garments (앞 20개)", garments(20))
    show("무신사 출처 옷 (source_name = musinsa_ml_project)", garments_by_source("musinsa_ml_project"))
    print()
    print("uniqlo_site / E422992-000:", garment_by_code("uniqlo_site", "E422992-000"))
