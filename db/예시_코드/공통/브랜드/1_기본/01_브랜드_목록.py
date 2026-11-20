# 목적: 브랜드 목록 보기 — 전체 목록, 나라별, 이름 하나로 찾기 (화면 첫 선택 상자·관리 화면)
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 기본 — 표 1개(garment.brands) SELECT + WHERE·ORDER BY
# 출력: 표 2개 — 브랜드 전체 4행(brand_id·이름·나라·모회사), 한국 브랜드 2행 + UNIQLO 찾기 결과 dict 1줄
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/1_기본/01_브랜드_목록.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 브랜드 전체 목록
def brands():
    sql = """
        SELECT b.brand_id, b.brand_name, b.country, b.group_name
        FROM garment.brands AS b
        ORDER BY b.brand_id
    """
    return query(sql)


# 목적: 나라(country, JP·KR 같은 두 글자) 하나의 브랜드
def brands_by_country(country="KR"):
    sql = """
        SELECT b.brand_id, b.brand_name, b.group_name
        FROM garment.brands AS b
        WHERE b.country = %s
        ORDER BY b.brand_name
    """
    return query(sql, (country,))


# 목적: 브랜드 이름으로 한 개 찾기 (없으면 None)
def brand_by_name(brand_name="UNIQLO"):
    sql = """
        SELECT b.brand_id, b.brand_name, b.country, b.group_name
        FROM garment.brands AS b
        WHERE b.brand_name = %s
    """
    rows = query(sql, (brand_name,))
    if len(rows) == 0:
        return None
    return rows[0]


if __name__ == "__main__":
    show("garment.brands 전체", brands())
    show("한국 브랜드 (country = KR)", brands_by_country("KR"))
    print()
    print("UNIQLO 찾기:", brand_by_name("UNIQLO"))
