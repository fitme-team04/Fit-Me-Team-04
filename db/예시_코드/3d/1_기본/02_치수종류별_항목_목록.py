# 목적: 치수 종류(measure_type: length·girth·height·breadth·depth)마다 정의된 항목 목록 (3D 몸통 단면 = 너비 breadth × 두께 depth 고르기)
# 누가 쓰나: 3D
# 난이도: 기본 — 표 1개(ref.measure_definitions) SELECT + WHERE 2조건·ORDER BY
# 출력: 종류 목록 + 표 3개(신체 breadth 3·depth 3행, 옷 실측 breadth 7행; measure_code·korean_name·body_part·iso_clause)
# 실행: .venv/bin/python db/예시_코드/3d/1_기본/02_치수종류별_항목_목록.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 정의된 치수 종류 이름 목록 (겹치지 않게 DISTINCT)
def measure_types():
    sql = """
        SELECT DISTINCT d.measure_type
        FROM ref.measure_definitions AS d
        ORDER BY d.measure_type
    """
    types = []
    for row in query(sql):
        types.append(row["measure_type"])
    return types


# 목적: 치수 종류 하나의 항목 목록. basis = body(신체) / garment(옷 실측)
def definitions_by_type(measure_type, basis="body"):
    sql = """
        SELECT d.measure_code, d.korean_name, d.body_part, d.iso_clause
        FROM ref.measure_definitions AS d
        WHERE d.measure_type = %s AND d.basis = %s
        ORDER BY d.body_part, d.measure_code
    """
    return query(sql, (measure_type, basis))


if __name__ == "__main__":
    print("치수 종류 목록:", measure_types())
    # 몸통 단면을 타원으로 만들 때: 가로 = breadth, 세로 = depth
    show("신체 breadth(너비) 항목 — 단면 가로", definitions_by_type("breadth"))
    show("신체 depth(두께) 항목 — 단면 세로", definitions_by_type("depth"))
    # 옷 쪽 breadth = 펼쳐 잰 단면 너비 (옷 패턴 폭)
    show("옷 실측 breadth(단면) 항목", definitions_by_type("breadth", "garment"))
