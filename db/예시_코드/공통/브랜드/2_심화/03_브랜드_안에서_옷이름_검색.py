# 목적: 브랜드 하나 안에서 옷 이름 키워드로 찾기 — 예: 유니클로 옷 중 이름에 "크루넥" 이 들어간 것
# 누가 쓰나: 공통 (3D / AI / 프론트. 브랜드 상세 화면 검색창)
# 난이도: 심화 — 2개 표 JOIN(브랜드 + 옷) + WHERE 브랜드 = %s AND 이름 LIKE %s
# 출력: 표 3개 — UNIQLO 이름 '크루넥' 3행, 'Long Sleeve' 2행, COVERNAT '티셔츠' 1행(garment_id·item_code·이름)
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/2_심화/03_브랜드_안에서_옷이름_검색.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 브랜드 이름 + 옷 이름 키워드 → 옷 목록
def search_in_brand(brand_name="UNIQLO", keyword="크루넥"):
    sql = """
        SELECT b.brand_name, g.garment_id, g.item_code, g.garment_name, g.target_gender
        FROM garment.brands AS b
        JOIN garment.garments AS g ON g.brand_id = b.brand_id
        WHERE b.brand_name = %s
          AND g.garment_name LIKE %s
        ORDER BY g.garment_id
    """
    pattern = "%" + keyword + "%"
    return query(sql, (brand_name, pattern))


if __name__ == "__main__":
    show("UNIQLO 옷 중 이름에 '크루넥'", search_in_brand("UNIQLO", "크루넥"))
    show("UNIQLO 옷 중 이름에 'Long Sleeve'", search_in_brand("UNIQLO", "Long Sleeve"))
    show("COVERNAT 옷 중 이름에 '티셔츠'", search_in_brand("COVERNAT", "티셔츠"))
