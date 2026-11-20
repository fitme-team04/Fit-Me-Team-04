# 목적: 브랜드를 옷 수로 순위 매기고 전체 옷 중 몇 % 인지 — 발표·보고서용 "브랜드 자료 순위표"
# 누가 쓰나: 공통 (3D / AI / 프론트. 자료 현황 보고)
# 난이도: 고급 — CTE(WITH) 로 브랜드별 개수를 먼저 만든 뒤 창 함수 RANK()·DENSE_RANK()·SUM() OVER () 로 순위·비율
# 출력: 표 1개 — 브랜드 옷 수 순위·비율 4행(garment_tally·rank_no·dense_rank_no·all_garment_tally·share_pct)
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/3_고급/03_브랜드_옷수_순위와_비율.py
# RANK: 같은 값이면 같은 순위, 다음 순위는 건너뜀 (1,2,3,3,5) / DENSE_RANK: 건너뛰지 않음 (1,2,3,3,4)
# SUM(x) OVER () = 행을 묶지 않고 모든 행의 합계를 각 행 옆에 붙임
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 브랜드별 옷 수 순위표 (옷 0벌 브랜드 포함)
def brand_ranking():
    sql = """
        WITH brand_counts AS (
            SELECT b.brand_id, b.brand_name, COUNT(g.garment_id) AS garment_tally
            FROM garment.brands AS b
            LEFT JOIN garment.garments AS g ON g.brand_id = b.brand_id
            GROUP BY b.brand_id, b.brand_name
        )
        SELECT bc.brand_name, bc.garment_tally,
               RANK()       OVER (ORDER BY bc.garment_tally DESC) AS rank_no,
               DENSE_RANK() OVER (ORDER BY bc.garment_tally DESC) AS dense_rank_no,
               SUM(bc.garment_tally) OVER ()                      AS all_garment_tally,
               ROUND(100 * bc.garment_tally / SUM(bc.garment_tally) OVER (), 1) AS share_pct
        FROM brand_counts AS bc
        ORDER BY rank_no, bc.brand_id
    """
    return query(sql)


if __name__ == "__main__":
    show("브랜드 옷 수 순위·비율", brand_ranking())
