# 목적: 브랜드마다 치수 항목별로 사이즈 몇 % 에 값이 있는지(커버리지) + 추천 규칙에 필요한데 브랜드에 아예 없는 옷 치수 항목
# 누가 쓰나: 공통 (3D / AI / 프론트. AI 학습 특징 고르기, 3D 모델에 쓸 수 있는 항목 확인)
# 난이도: 고급 — CTE 2개(브랜드별 사이즈 수, 브랜드×항목별 실측 사이즈 수) + 5개 표 JOIN + 비율 계산식 / CROSS JOIN + NOT EXISTS
# 출력: 표 2개 — 브랜드×치수 항목 커버리지 10행(measure_code·coverage_pct), 추천 규칙에 필요한데 없는 항목 10행
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/3_고급/09_브랜드_치수항목_커버리지.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: (브랜드, 치수 항목, basis)마다 값이 있는 사이즈 수 / 브랜드 전체 사이즈 수 (%)
def measure_coverage():
    sql = """
        WITH brand_sizes AS (
            SELECT b.brand_id, b.brand_name, COUNT(s.size_id) AS size_tally
            FROM garment.brands AS b
            JOIN garment.garments AS g ON g.brand_id = b.brand_id
            JOIN garment.sizes AS s ON s.garment_id = g.garment_id
            GROUP BY b.brand_id, b.brand_name
        ),
        measured AS (
            SELECT g.brand_id, gm.measure_code, gm.basis,
                   COUNT(DISTINCT gm.size_id) AS measured_size_tally
            FROM garment.garments AS g
            JOIN garment.sizes AS s ON s.garment_id = g.garment_id
            JOIN garment.measures AS gm ON gm.size_id = s.size_id
            GROUP BY g.brand_id, gm.measure_code, gm.basis
        )
        SELECT bs.brand_name, m.basis, m.measure_code, d.korean_name,
               m.measured_size_tally, bs.size_tally,
               ROUND(100 * m.measured_size_tally / bs.size_tally, 1) AS coverage_pct
        FROM brand_sizes AS bs
        JOIN measured AS m ON m.brand_id = bs.brand_id
        JOIN ref.measure_definitions AS d ON d.measure_code = m.measure_code
        ORDER BY bs.brand_id, m.basis, coverage_pct DESC, m.measure_code
    """
    return query(sql)


# 목적: 사이즈가 있는 브랜드 × 추천 규칙(ref.measure_maps)의 옷 치수 항목 중, 그 브랜드에 값이 하나도 없는 것
def missing_map_measures():
    sql = """
        SELECT b.brand_name, mm.garment_measure_code, d.korean_name, mm.body_measure_code
        FROM garment.brands AS b
        CROSS JOIN ref.measure_maps AS mm
        JOIN ref.measure_definitions AS d ON d.measure_code = mm.garment_measure_code
        WHERE EXISTS (
                  SELECT 1
                  FROM garment.garments AS g
                  JOIN garment.sizes AS s ON s.garment_id = g.garment_id
                  WHERE g.brand_id = b.brand_id
              )
          AND NOT EXISTS (
                  SELECT 1
                  FROM garment.garments AS g
                  JOIN garment.sizes AS s ON s.garment_id = g.garment_id
                  JOIN garment.measures AS gm ON gm.size_id = s.size_id
                  WHERE g.brand_id = b.brand_id
                    AND gm.measure_code = mm.garment_measure_code
                    AND gm.basis = 'garment'
              )
        ORDER BY b.brand_id, mm.garment_measure_code
    """
    return query(sql)


if __name__ == "__main__":
    show("브랜드 × 치수 항목 커버리지 (값 있는 사이즈 / 전체 사이즈)", measure_coverage())
    show("추천 규칙에 필요한데 브랜드에 없는 옷 치수 항목", missing_map_measures())
