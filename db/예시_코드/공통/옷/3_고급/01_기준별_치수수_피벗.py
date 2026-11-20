# 목적: 옷 실측(basis = garment) vs 권장 신체 범위(basis = body)를 옷 1벌 = 1행 가로표로 — 부위별 개수·사이즈별 자료 상태까지
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 고급 — 표 4개 LEFT JOIN(garments + sizes + measures + measure_definitions) + 조건부 집계 피벗 SUM(CASE ...)·COUNT(DISTINCT CASE ...)
# 출력: 옷마다 basis·부위별 치수 행 수 가로 피벗 3행, 사이즈별 자료 상태(data_status) 크루넥T 11행·COVERNAT 6행
# 실행: .venv/bin/python db/예시_코드/공통/옷/3_고급/01_기준별_치수수_피벗.py
# 세로로 긴 판(옷 × basis 마다 1행)은 2_심화/07_기준별_치수수.py
# SUM(CASE WHEN 조건 THEN 1 ELSE 0 END) = 조건에 맞는 행 수 → 값마다 열 하나씩 만드는 "피벗"
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 옷마다 사이즈 수 + basis 별 행 수 + 부위별 행 수 + basis 별 자료 있는 사이즈 수 (사이즈가 있는 옷만)
def basis_pivot_by_garment():
    sql = """
        SELECT g.garment_id, g.item_code,
               COUNT(DISTINCT s.size_id) AS size_tally,
               SUM(CASE WHEN gm.basis = 'garment' THEN 1 ELSE 0 END) AS garment_rows,
               SUM(CASE WHEN gm.basis = 'body'    THEN 1 ELSE 0 END) AS body_rows,
               SUM(CASE WHEN d.body_part = 'torso' THEN 1 ELSE 0 END) AS torso_rows,
               SUM(CASE WHEN d.body_part = 'arm'   THEN 1 ELSE 0 END) AS arm_rows,
               COUNT(DISTINCT CASE WHEN gm.basis = 'garment' THEN s.size_id END) AS sizes_with_garment,
               COUNT(DISTINCT CASE WHEN gm.basis = 'body'    THEN s.size_id END) AS sizes_with_body
        FROM garment.garments AS g
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        LEFT JOIN garment.measures AS gm ON gm.size_id = s.size_id
        LEFT JOIN ref.measure_definitions AS d ON d.measure_code = gm.measure_code
        GROUP BY g.garment_id, g.item_code
        ORDER BY g.garment_id
    """
    return query(sql)


# 목적: 옷 하나의 사이즈마다 basis 별 행 수 + 자료 상태(both / garment_only / body_only / none)
def basis_status_by_size(source_name="uniqlo_site", item_code="E422992-000"):
    sql = """
        SELECT s.size_label, s.region,
               SUM(CASE WHEN gm.basis = 'garment' THEN 1 ELSE 0 END) AS garment_rows,
               SUM(CASE WHEN gm.basis = 'body'    THEN 1 ELSE 0 END) AS body_rows,
               CASE
                   WHEN SUM(CASE WHEN gm.basis = 'garment' THEN 1 ELSE 0 END) > 0
                    AND SUM(CASE WHEN gm.basis = 'body' THEN 1 ELSE 0 END) > 0 THEN 'both'
                   WHEN SUM(CASE WHEN gm.basis = 'garment' THEN 1 ELSE 0 END) > 0 THEN 'garment_only'
                   WHEN SUM(CASE WHEN gm.basis = 'body' THEN 1 ELSE 0 END) > 0 THEN 'body_only'
                   ELSE 'none'
               END AS data_status
        FROM garment.garments AS g
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        LEFT JOIN garment.measures AS gm ON gm.size_id = s.size_id
        LEFT JOIN ref.measure_definitions AS d ON d.measure_code = gm.measure_code
        WHERE g.source_name = %s
          AND g.item_code = %s
        GROUP BY s.size_id, s.size_label, s.region
        ORDER BY s.region, s.size_id
    """
    return query(sql, (source_name, item_code))


if __name__ == "__main__":
    show("옷마다 basis·부위별 치수 행 수 (가로 피벗)", basis_pivot_by_garment())
    show("크루넥T(E422992-000) 사이즈별 자료 상태", basis_status_by_size("uniqlo_site", "E422992-000"))
    show("COVERNAT(1848166) 사이즈별 자료 상태", basis_status_by_size("musinsa_ml_project", "1848166"))
