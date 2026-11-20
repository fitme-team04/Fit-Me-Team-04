# 목적: 추천 화면 첫 드롭다운 "브랜드 고르기" 선택값 — 브랜드 전체 또는 나라별 (value = brand_id)
# 누가 쓰나: 프론트 (브랜드 자세한 조회는 공통/브랜드)
# 난이도: 기본 — 표 1개(garment.brands) SELECT + WHERE 한 줄(선택) + ORDER BY
# 출력: 브랜드 드롭다운(value·label) 전체 4행, 한국 브랜드(country = KR)만 2행
# 실행: .venv/bin/python db/예시_코드/front/1_기본/08_브랜드_선택목록.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 브랜드 행 목록. country 를 주면 그 나라 브랜드만 (예: 'KR')
def brand_rows(country=None):
    if country is None:
        sql = """
            SELECT b.brand_id, b.brand_name, b.country
            FROM garment.brands AS b
            ORDER BY b.brand_name
        """
        return query(sql)
    sql = """
        SELECT b.brand_id, b.brand_name, b.country
        FROM garment.brands AS b
        WHERE b.country = %s
        ORDER BY b.brand_name
    """
    return query(sql, (country,))


# 목적: 행 목록 → 드롭다운 선택값 [{"value": brand_id, "label": "UNIQLO (JP)"}]
def brand_options(country=None):
    options = []
    for row in brand_rows(country):
        options.append({"value": row["brand_id"], "label": row["brand_name"] + " (" + row["country"] + ")"})
    return options


if __name__ == "__main__":
    show("브랜드 드롭다운 (전체)", brand_options())
    show("브랜드 드롭다운 (한국 브랜드만, country = KR)", brand_options("KR"))
