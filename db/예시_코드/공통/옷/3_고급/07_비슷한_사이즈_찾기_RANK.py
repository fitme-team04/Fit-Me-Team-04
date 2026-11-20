# 목적: 기준 사이즈 하나(예: 크루넥T KR M)와 옷 실측이 가장 비슷한 다른 사이즈를 순위로 — "이 옷 M 이 맞았다면 저 옷은 무엇"
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 고급 — CTE 2개 + 4개 표 JOIN + 계산식 AVG(ABS(차이)) + 창 함수 RANK() OVER (ORDER BY ...)
# 출력: 비슷한 사이즈 순위 — 크루넥T KR M 기준 3행, COVERNAT KR M 기준 3행 (공통 항목 수·평균/최대 차이 cm)
# 실행: .venv/bin/python db/예시_코드/공통/옷/3_고급/07_비슷한_사이즈_찾기_RANK.py
# 같은 항목끼리만 비교 → 항목마다 |후보 − 기준| 의 평균이 작을수록 비슷함. RANK 는 같은 값이면 같은 순위(1, 1, 3 ...)
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 기준 사이즈와 공통 항목이 min_shared 개 이상인 다른 사이즈를 평균 차이 순위로
def similar_sizes(source_name="uniqlo_site", item_code="E422992-000", size_label="M", region="KR", min_shared=2):
    sql = """
        WITH base AS (
            SELECT s.size_id, gm.measure_code, gm.value_cm
            FROM garment.garments AS g
            JOIN garment.sizes AS s ON s.garment_id = g.garment_id
            JOIN garment.measures AS gm ON gm.size_id = s.size_id
            WHERE g.source_name = %s AND g.item_code = %s
              AND s.size_label = %s AND s.region = %s
              AND gm.basis = 'garment'
        ),
        candidates AS (
            SELECT g.source_name, g.item_code, s.size_label, s.region,
                   COUNT(*) AS shared_measures,
                   ROUND(AVG(ABS(gm.value_cm - b.value_cm)), 2) AS avg_abs_diff_cm,
                   MAX(ABS(gm.value_cm - b.value_cm)) AS max_abs_diff_cm
            FROM garment.garments AS g
            JOIN garment.sizes AS s ON s.garment_id = g.garment_id
            JOIN garment.measures AS gm ON gm.size_id = s.size_id AND gm.basis = 'garment'
            JOIN base AS b ON b.measure_code = gm.measure_code
            WHERE s.size_id <> b.size_id
            GROUP BY g.source_name, g.item_code, s.size_id, s.size_label, s.region
            HAVING COUNT(*) >= %s
        )
        SELECT RANK() OVER (ORDER BY c.avg_abs_diff_cm) AS similarity_rank,
               c.source_name, c.item_code, c.size_label, c.region,
               c.shared_measures, c.avg_abs_diff_cm, c.max_abs_diff_cm
        FROM candidates AS c
        ORDER BY similarity_rank, c.item_code
    """
    return query(sql, (source_name, item_code, size_label, region, min_shared))


if __name__ == "__main__":
    show("크루넥T KR M 과 비슷한 사이즈", similar_sizes("uniqlo_site", "E422992-000", "M", "KR", 2))
    show("COVERNAT 1848166 KR M 과 비슷한 사이즈", similar_sizes("musinsa_ml_project", "1848166", "M", "KR", 2))
