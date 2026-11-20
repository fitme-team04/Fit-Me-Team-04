# 목적: 브랜드가 있는 나라 목록(중복 없이) — 프론트 "나라" 선택 상자에 넣을 값
# 누가 쓰나: 공통 (3D / AI / 프론트. 프론트 나라 선택 상자)
# 난이도: 기본 — 표 1개(garment.brands) SELECT DISTINCT + ORDER BY
# 출력: 표 2개 — 브랜드가 있는 나라 2행(JP·KR), (나라, 모회사) 조합 3행(country·group_name)
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/1_기본/06_브랜드_나라_목록.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 나라 코드 목록 (같은 나라 브랜드가 여럿이어도 한 번만)
def countries():
    sql = """
        SELECT DISTINCT b.country
        FROM garment.brands AS b
        ORDER BY b.country
    """
    return query(sql)


# 목적: (나라, 모회사) 조합 목록 — DISTINCT 는 고른 열 전체가 같을 때만 하나로 합침
def country_group_pairs():
    sql = """
        SELECT DISTINCT b.country, b.group_name
        FROM garment.brands AS b
        ORDER BY b.country, b.group_name
    """
    return query(sql)


if __name__ == "__main__":
    show("브랜드가 있는 나라", countries())
    show("(나라, 모회사) 조합", country_group_pairs())
