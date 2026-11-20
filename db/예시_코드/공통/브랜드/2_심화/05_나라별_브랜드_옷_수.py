# 목적: 나라(country)마다 브랜드 수와 옷 수 — 일본·한국 브랜드 자료가 각각 얼마나 모였는지
# 누가 쓰나: 공통 (3D / AI / 프론트. AI 학습 자료 나라 치우침 확인)
# 난이도: 심화 — 2개 표 LEFT JOIN(브랜드 + 옷) + GROUP BY country + COUNT(DISTINCT ...)
# 출력: 표 1개 — 나라별 브랜드 수·옷 수 2행(JP 브랜드 2·옷 12, KR 브랜드 2·옷 1)
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/2_심화/05_나라별_브랜드_옷_수.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 나라별 (브랜드 수, 옷 수). 옷이 여러 벌이면 브랜드가 여러 번 붙으므로 브랜드는 DISTINCT 로 셈
def tally_by_country():
    sql = """
        SELECT b.country,
               COUNT(DISTINCT b.brand_id)   AS brand_tally,
               COUNT(g.garment_id)          AS garment_tally
        FROM garment.brands AS b
        LEFT JOIN garment.garments AS g ON g.brand_id = b.brand_id
        GROUP BY b.country
        ORDER BY garment_tally DESC, b.country
    """
    return query(sql)


if __name__ == "__main__":
    show("나라별 브랜드 수·옷 수", tally_by_country())
