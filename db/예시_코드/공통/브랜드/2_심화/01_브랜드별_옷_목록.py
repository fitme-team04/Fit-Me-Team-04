# 목적: 브랜드 하나의 옷 불러오기 — 예: 유니클로 옷 전부, 유니클로 여성 옷만, 종류(category)별 개수
# 누가 쓰나: 공통 (3D / AI / 프론트. 프론트 두 번째 선택 상자)
# 난이도: 심화 — 2개 표 JOIN(브랜드 + 옷) + 선택 조건 (%s IS NULL OR ...) + GROUP BY COUNT
# 출력: 표 5개 — UNIQLO 옷 전부 12행, 여성 9행, 상의 남녀공용 2행, 종류·성별별 개수 3행, COVERNAT 옷 1행
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/2_심화/01_브랜드별_옷_목록.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 브랜드 이름 → 그 브랜드 옷 목록. category·target_gender 는 None 이면 조건을 안 씀 (전부)
def brand_garments(brand_name="UNIQLO", category=None, target_gender=None):
    sql = """
        SELECT g.garment_id, g.source_name, g.item_code, g.garment_name,
               g.category, g.target_gender, g.fit
        FROM garment.garments AS g
        JOIN garment.brands AS b ON b.brand_id = g.brand_id
        WHERE b.brand_name = %s
          AND (%s IS NULL OR g.category = %s)
          AND (%s IS NULL OR g.target_gender = %s)
        ORDER BY g.garment_id
    """
    params = (brand_name, category, category, target_gender, target_gender)
    return query(sql, params)


# 목적: 브랜드 하나의 종류(category)·대상 성별(target_gender)별 옷 개수
def garment_tally(brand_name="UNIQLO"):
    sql = """
        SELECT g.category, g.target_gender, COUNT(*) AS garment_tally
        FROM garment.garments AS g
        JOIN garment.brands AS b ON b.brand_id = g.brand_id
        WHERE b.brand_name = %s
        GROUP BY g.category, g.target_gender
        ORDER BY g.category, g.target_gender
    """
    return query(sql, (brand_name,))


if __name__ == "__main__":
    # 유니클로 옷 전부 불러오기 (조건 없이 브랜드 이름만)
    show("UNIQLO 옷 전부", brand_garments("UNIQLO"))
    # 조건을 하나씩 더하기
    show("UNIQLO 여성 옷 (target_gender = female)", brand_garments("UNIQLO", target_gender="female"))
    show("UNIQLO 상의 남녀공용 (category = 상의, target_gender = unisex)", brand_garments("UNIQLO", "상의", "unisex"))
    show("UNIQLO 종류·성별별 옷 개수", garment_tally("UNIQLO"))
    # 다른 브랜드도 이름만 바꾸면 됨
    show("COVERNAT 옷 전부", brand_garments("COVERNAT"))
