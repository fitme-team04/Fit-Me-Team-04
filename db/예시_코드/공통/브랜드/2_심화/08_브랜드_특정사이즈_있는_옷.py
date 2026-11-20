# 목적: 브랜드 하나에서 특정 사이즈(예: KR XL)가 나오는 옷만 — "유니클로에서 XL 있는 옷 보여 줘"
# 누가 쓰나: 공통 (3D / AI / 프론트. 프론트 사이즈 필터)
# 난이도: 심화 — 2개 표 JOIN(브랜드 + 옷) + WHERE ... IN (SELECT ... FROM 사이즈) 하위 질의
# 출력: 표 3개 — UNIQLO KR XL·UNIQLO US M·COVERNAT KR XXL 이 있는 옷 각 1행(garment_id·item_code·이름)
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/2_심화/08_브랜드_특정사이즈_있는_옷.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 브랜드 + (사이즈 표기, 지역) → 그 사이즈가 등록된 옷. 하위 질의가 먼저 garment_id 목록을 만들고 IN 으로 거름
def garments_with_size(brand_name="UNIQLO", size_label="XL", region="KR"):
    sql = """
        SELECT b.brand_name, g.garment_id, g.item_code, g.garment_name
        FROM garment.brands AS b
        JOIN garment.garments AS g ON g.brand_id = b.brand_id
        WHERE b.brand_name = %s
          AND g.garment_id IN (
              SELECT s.garment_id
              FROM garment.sizes AS s
              WHERE s.size_label = %s
                AND s.region = %s
          )
        ORDER BY g.garment_id
    """
    return query(sql, (brand_name, size_label, region))


if __name__ == "__main__":
    show("UNIQLO 에서 KR XL 이 있는 옷", garments_with_size("UNIQLO", "XL", "KR"))
    show("UNIQLO 에서 US M 이 있는 옷", garments_with_size("UNIQLO", "M", "US"))
    show("COVERNAT 에서 KR XXL 이 있는 옷", garments_with_size("COVERNAT", "XXL", "KR"))
