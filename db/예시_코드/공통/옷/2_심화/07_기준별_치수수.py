# 목적: 옷마다 옷 실측(basis = garment)과 권장 신체 범위(basis = body)가 각각 몇 행인지 — 추천 규칙(여유분 / 범위)을 어느 옷에 쓸 수 있는지
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 심화 — 표 3개 JOIN(garments + sizes + measures) + GROUP BY 옷 × basis (세로로 긴 표. 가로 피벗 판은 3_고급/01_기준별_치수수_피벗.py)
# 출력: (옷, basis)별 치수 행 수·사이즈 수 4행, 권장 신체 범위(body) 있는 옷 1행, 옷 실측(garment) 있는 옷 3행
# 실행: .venv/bin/python db/예시_코드/공통/옷/2_심화/07_기준별_치수수.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: (옷, basis)마다 치수 행 수 + 치수가 있는 사이즈 수
def basis_tally_by_garment():
    sql = """
        SELECT g.garment_id, g.item_code, gm.basis,
               COUNT(*) AS row_tally,
               COUNT(DISTINCT s.size_id) AS size_tally
        FROM garment.garments AS g
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        JOIN garment.measures AS gm ON gm.size_id = s.size_id
        GROUP BY g.garment_id, g.item_code, gm.basis
        ORDER BY g.garment_id, gm.basis
    """
    return query(sql)


# 목적: basis 하나의 치수가 있는 옷 목록 (예: 권장 신체 범위가 있는 옷)
def garments_with_basis(basis="body"):
    sql = """
        SELECT g.garment_id, g.item_code, g.garment_name, COUNT(*) AS row_tally
        FROM garment.garments AS g
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        JOIN garment.measures AS gm ON gm.size_id = s.size_id
        WHERE gm.basis = %s
        GROUP BY g.garment_id, g.item_code, g.garment_name
        ORDER BY g.garment_id
    """
    return query(sql, (basis,))


if __name__ == "__main__":
    show("(옷, basis)별 치수 행 수", basis_tally_by_garment())
    show("권장 신체 범위(basis = body)가 있는 옷", garments_with_basis("body"))
    show("옷 실측(basis = garment)이 있는 옷", garments_with_basis("garment"))
