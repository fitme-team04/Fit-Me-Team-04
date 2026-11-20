# 목적: 옷 한 벌에서 "다른 사이즈에는 있는데 이 사이즈에는 없는" 치수 항목을 (사이즈, 항목) 단위로 찾기 — 채워야 할 칸 목록
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 고급 — CTE 3개(대상 옷 / 그 옷이 쓰는 항목 / 그 옷의 사이즈) + CROSS JOIN 으로 모든 칸 만들기 + NOT EXISTS 로 빈 칸만
# 출력: kobo mens-tops 빠진 칸(사이즈×항목) 4행, 크루넥T 사이즈별 전체 칸 수·빠진 칸 수 11행
# 실행: .venv/bin/python db/예시_코드/공통/옷/3_고급/05_빠진_치수_NOT_EXISTS.py
# CROSS JOIN = 두 표의 모든 짝(사이즈 3개 × 항목 2개 = 6칸). 그중 measures 에 없는 칸이 "빠진 치수"
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 옷(출처 + 상품번호)의 (사이즈, basis, 항목) 중 비어 있는 칸
def missing_cells(source_name="kobo_garment_measurements", item_code="mens-tops"):
    sql = """
        WITH target AS (
            SELECT g.garment_id
            FROM garment.garments AS g
            WHERE g.source_name = %s AND g.item_code = %s
        ),
        used_codes AS (
            SELECT DISTINCT gm.measure_code, gm.basis
            FROM garment.sizes AS s
            JOIN target AS t ON t.garment_id = s.garment_id
            JOIN garment.measures AS gm ON gm.size_id = s.size_id
        ),
        target_sizes AS (
            SELECT s.size_id, s.size_label, s.region
            FROM garment.sizes AS s
            JOIN target AS t ON t.garment_id = s.garment_id
        )
        SELECT ts.size_id, ts.size_label, ts.region, uc.basis, uc.measure_code, d.korean_name
        FROM target_sizes AS ts
        CROSS JOIN used_codes AS uc
        JOIN ref.measure_definitions AS d ON d.measure_code = uc.measure_code
        WHERE NOT EXISTS (SELECT 1
                          FROM garment.measures AS x
                          WHERE x.size_id = ts.size_id
                            AND x.measure_code = uc.measure_code
                            AND x.basis = uc.basis)
        ORDER BY ts.region, ts.size_id, uc.basis, uc.measure_code
    """
    return query(sql, (source_name, item_code))


# 목적: 옷 한 벌의 사이즈마다 빠진 칸 수 / 전체 칸 수 (위와 같은 CTE + GROUP BY)
def missing_tally_by_size(source_name="uniqlo_site", item_code="E422992-000"):
    sql = """
        WITH target AS (
            SELECT g.garment_id
            FROM garment.garments AS g
            WHERE g.source_name = %s AND g.item_code = %s
        ),
        used_codes AS (
            SELECT DISTINCT gm.measure_code, gm.basis
            FROM garment.sizes AS s
            JOIN target AS t ON t.garment_id = s.garment_id
            JOIN garment.measures AS gm ON gm.size_id = s.size_id
        )
        SELECT s.size_label, s.region,
               COUNT(*) AS cell_tally,
               SUM(CASE WHEN NOT EXISTS (SELECT 1 FROM garment.measures AS x
                                         WHERE x.size_id = s.size_id
                                           AND x.measure_code = uc.measure_code
                                           AND x.basis = uc.basis)
                        THEN 1 ELSE 0 END) AS missing_tally
        FROM garment.sizes AS s
        JOIN target AS t ON t.garment_id = s.garment_id
        CROSS JOIN used_codes AS uc
        GROUP BY s.size_id, s.size_label, s.region
        ORDER BY s.region, s.size_id
    """
    return query(sql, (source_name, item_code))


if __name__ == "__main__":
    show("kobo mens-tops 빠진 칸 (사이즈 × 항목)", missing_cells("kobo_garment_measurements", "mens-tops"))
    show("크루넥T(E422992-000) 사이즈별 빠진 칸 수", missing_tally_by_size("uniqlo_site", "E422992-000"))
