# 목적: 부위 × 기준(신체·옷)별 정의된 치수 항목 수와 코드 묶음, 종류별 항목 수 (3D 부위마다 몇 개 값을 받을 수 있는지)
# 누가 쓰나: 3D
# 난이도: 심화 — GROUP BY 2열 + COUNT·GROUP_CONCAT, GROUP BY + HAVING (표 1개)
# 출력: 부위×기준별 항목 수 표(8행; body_part·basis·measure_tally·codes) + 신체 치수 종류별 항목 수 표(3개 이상, 5행)
# 실행: .venv/bin/python db/예시_코드/3d/2_심화/01_부위별_항목수_집계.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 부위 × basis 마다 항목 수 + 코드 목록
def tally_by_part():
    sql = """
        SELECT d.body_part, d.basis, COUNT(*) AS measure_tally,
               GROUP_CONCAT(d.measure_code ORDER BY d.measure_code SEPARATOR ', ') AS codes
        FROM ref.measure_definitions AS d
        GROUP BY d.body_part, d.basis
        ORDER BY d.basis, d.body_part
    """
    return query(sql)


# 목적: 신체(body) 치수 종류별 항목 수, min_tally 개 이상인 종류만 (HAVING)
def body_types_with_at_least(min_tally):
    sql = """
        SELECT d.measure_type, COUNT(*) AS measure_tally
        FROM ref.measure_definitions AS d
        WHERE d.basis = 'body'
        GROUP BY d.measure_type
        HAVING COUNT(*) >= %s
        ORDER BY measure_tally DESC
    """
    return query(sql, (min_tally,))


if __name__ == "__main__":
    show("부위 × 기준별 항목 수", tally_by_part())
    show("신체 치수 종류별 항목 수 (3개 이상)", body_types_with_at_least(3))
