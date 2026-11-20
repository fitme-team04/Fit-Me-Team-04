# 목적: 옷 종류(category)·대상 성별마다 소매길이 최대·최소·평균 — 종류별 치수 폭 감 잡기 (어느 사이즈인지까지는 3_고급/06)
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 심화 — 표 3개 JOIN(garments + sizes + measures) + GROUP BY + MAX·MIN·AVG
# 출력: 종류별 소매길이 최대·최소·평균·폭 1행, 종류·성별 소매길이 1행, 종류별 가슴단면 1행 (모두 상의)
# 실행: .venv/bin/python db/예시_코드/공통/옷/2_심화/09_종류별_소매길이_최대최소.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 종류마다 치수 하나의 옷 실측 최대·최소·평균
def measure_range_by_category(measure_code="sleeve_length"):
    sql = """
        SELECT g.category,
               COUNT(*) AS size_tally,
               MAX(gm.value_cm) AS max_cm,
               MIN(gm.value_cm) AS min_cm,
               ROUND(AVG(gm.value_cm), 1) AS avg_cm,
               MAX(gm.value_cm) - MIN(gm.value_cm) AS spread_cm
        FROM garment.garments AS g
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        JOIN garment.measures AS gm ON gm.size_id = s.size_id
        WHERE gm.measure_code = %s
          AND gm.basis = 'garment'
        GROUP BY g.category
        ORDER BY g.category
    """
    return query(sql, (measure_code,))


# 목적: (종류, 대상 성별)마다 치수 하나의 최대·최소
def measure_range_by_category_gender(measure_code="sleeve_length"):
    sql = """
        SELECT g.category, g.target_gender,
               COUNT(*) AS size_tally,
               MAX(gm.value_cm) AS max_cm,
               MIN(gm.value_cm) AS min_cm
        FROM garment.garments AS g
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        JOIN garment.measures AS gm ON gm.size_id = s.size_id
        WHERE gm.measure_code = %s
          AND gm.basis = 'garment'
        GROUP BY g.category, g.target_gender
        ORDER BY g.category, g.target_gender
    """
    return query(sql, (measure_code,))


if __name__ == "__main__":
    show("종류별 소매길이 최대·최소·평균", measure_range_by_category("sleeve_length"))
    show("종류·성별 소매길이 최대·최소", measure_range_by_category_gender("sleeve_length"))
    show("종류별 가슴단면 최대·최소·평균", measure_range_by_category("chest_width"))
