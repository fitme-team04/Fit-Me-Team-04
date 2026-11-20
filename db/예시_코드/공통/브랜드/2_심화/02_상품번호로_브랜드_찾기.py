# 목적: 출처 + 상품번호로 "이 옷은 어느 브랜드인가" 찾기 — 브랜드가 없는 옷도 '(브랜드 없음)' 으로 나오게
# 누가 쓰나: 공통 (3D / AI / 프론트. 상품 링크·수집 자료에서 브랜드 표시)
# 난이도: 심화 — 2개 표 LEFT JOIN(옷 + 브랜드) + COALESCE 로 NULL 대신 글자
# 출력: 표 3개 — 상품번호 3건의 브랜드 각 1행(item_code·brand_name·나라·모회사), kobo 옷은 '(브랜드 없음)'
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/2_심화/02_상품번호로_브랜드_찾기.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: (출처, 상품번호) → 옷 이름 + 브랜드 정보. JOIN 이면 브랜드 없는 옷이 빠지므로 LEFT JOIN
def brand_of_item(source_name="uniqlo_site", item_code="E422992-000"):
    sql = """
        SELECT g.source_name, g.item_code, g.garment_name,
               COALESCE(b.brand_name, '(브랜드 없음)') AS brand_name,
               b.country, b.group_name
        FROM garment.garments AS g
        LEFT JOIN garment.brands AS b ON b.brand_id = g.brand_id
        WHERE g.source_name = %s
          AND g.item_code = %s
    """
    return query(sql, (source_name, item_code))


if __name__ == "__main__":
    show("uniqlo_site / E422992-000 의 브랜드", brand_of_item("uniqlo_site", "E422992-000"))
    show("musinsa_ml_project / 1848166 의 브랜드", brand_of_item("musinsa_ml_project", "1848166"))
    show("kobo_garment_measurements / mens-tops 의 브랜드", brand_of_item("kobo_garment_measurements", "mens-tops"))
