# 목적: 신체 치수 코드를 뼈대용(길이·높이 = length·height)과 살 두께용(둘레 = girth)으로 나누기 (3D 리그 뼈 길이 ↔ 메시 단면 둘레)
# 누가 쓰나: 3D
# 난이도: 기본 — 표 1개(ref.measure_definitions) SELECT + WHERE IN·ORDER BY
# 출력: 뼈대용 길이·높이 코드 표(8행)·둘레 코드 표(11행; measure_code·korean_name·body_part) + 두 코드 목록
# 실행: .venv/bin/python db/예시_코드/3d/1_기본/03_뼈대길이_둘레_코드_구분.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 뼈대(리그) 길이를 정할 신체 코드 — length(구간 길이) + height(바닥에서 높이)
def skeleton_codes():
    sql = """
        SELECT d.measure_code, d.korean_name, d.body_part, d.measure_type
        FROM ref.measure_definitions AS d
        WHERE d.basis = 'body' AND d.measure_type IN ('length', 'height')
        ORDER BY d.measure_type, d.body_part, d.measure_code
    """
    return query(sql)


# 목적: 메시 단면 크기를 정할 신체 둘레 코드 (girth)
def girth_codes():
    sql = """
        SELECT d.measure_code, d.korean_name, d.body_part
        FROM ref.measure_definitions AS d
        WHERE d.basis = 'body' AND d.measure_type = 'girth'
        ORDER BY d.body_part, d.measure_code
    """
    return query(sql)


# 목적: 행 목록에서 measure_code 만 뽑아 리스트로
def codes_of(rows):
    codes = []
    for row in rows:
        codes.append(row["measure_code"])
    return codes


if __name__ == "__main__":
    bones = skeleton_codes()
    girths = girth_codes()
    show("뼈대용 길이·높이 코드 (length·height)", bones)
    show("단면용 둘레 코드 (girth)", girths)
    print()
    print("뼈대 코드:", codes_of(bones))
    print("둘레 코드:", codes_of(girths))
