# 목적: 브랜드가 몇 개인지 한 줄 요약 — 전체 수, 모회사가 채워진 수, 나라 수, 모회사 수 (관리 화면 첫 줄)
# 누가 쓰나: 공통 (3D / AI / 프론트. 관리자 자료 현황)
# 난이도: 기본 — 표 1개(garment.brands) COUNT(*) · COUNT(열) · COUNT(DISTINCT 열) (GROUP BY 없이 표 전체 1행)
# 출력: 표 2개 — 브랜드 수 요약 1행(전체 4·모회사 있음 3·나라 2·모회사 2), 일본(JP) 브랜드 수 1행(2)
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/1_기본/08_브랜드_수_요약.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 표 전체 요약 1행. COUNT(*) 는 모든 행, COUNT(열) 은 그 열이 NULL 이 아닌 행만 셈
def brand_summary():
    sql = """
        SELECT COUNT(*)                     AS brand_tally,
               COUNT(b.group_name)          AS with_group_tally,
               COUNT(DISTINCT b.country)    AS country_tally,
               COUNT(DISTINCT b.group_name) AS group_tally
        FROM garment.brands AS b
    """
    return query(sql)


# 목적: 나라 하나의 브랜드 수 (WHERE 로 거른 뒤 COUNT)
def brand_tally_in_country(country="JP"):
    sql = """
        SELECT COUNT(*) AS brand_tally
        FROM garment.brands AS b
        WHERE b.country = %s
    """
    return query(sql, (country,))


if __name__ == "__main__":
    show("브랜드 수 요약", brand_summary())
    show("일본(JP) 브랜드 수", brand_tally_in_country("JP"))
