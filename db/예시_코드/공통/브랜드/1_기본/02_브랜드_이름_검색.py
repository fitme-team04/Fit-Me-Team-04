# 목적: 브랜드 이름 일부(키워드)로 찾기 — 검색창에 "MUSINSA" 일부만 쳐도 나오게 (정확한 이름을 모를 때)
# 누가 쓰나: 공통 (3D / AI / 프론트. 프론트 브랜드 검색창)
# 난이도: 기본 — 표 1개(garment.brands) SELECT + WHERE LIKE '%키워드%' + ORDER BY
# 출력: 표 3개 — 이름에 MUSINSA 1행, 이름에 NAT 1행, G로 시작(자동 완성) 1행(brand_id·brand_name 등)
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/1_기본/02_브랜드_이름_검색.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 이름에 keyword 가 들어간 브랜드 (앞뒤에 % 를 붙여 "어디든 포함" 검색)
def search_brands(keyword="MUSINSA"):
    sql = """
        SELECT b.brand_id, b.brand_name, b.country, b.group_name
        FROM garment.brands AS b
        WHERE b.brand_name LIKE %s
        ORDER BY b.brand_name
    """
    pattern = "%" + keyword + "%"
    return query(sql, (pattern,))


# 목적: 이름이 prefix 로 시작하는 브랜드 (자동 완성용, 뒤에만 % 를 붙임)
def brands_starting_with(prefix="G"):
    sql = """
        SELECT b.brand_id, b.brand_name
        FROM garment.brands AS b
        WHERE b.brand_name LIKE %s
        ORDER BY b.brand_name
    """
    pattern = prefix + "%"
    return query(sql, (pattern,))


if __name__ == "__main__":
    show("이름에 MUSINSA 가 들어간 브랜드", search_brands("MUSINSA"))
    show("이름에 NAT 가 들어간 브랜드", search_brands("NAT"))
    show("G 로 시작하는 브랜드 (자동 완성)", brands_starting_with("G"))
