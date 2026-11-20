# 목적: 신체 부위(full·torso·arm·leg·neck)마다 어떤 치수 항목이 정의돼 있는지 목록 (3D 모델에 맞출 치수 고르기)
# 누가 쓰나: 3D
# 난이도: 기본 — 표 1개(ref.measure_definitions) SELECT + WHERE·ORDER BY
# 출력: 부위 목록 + 부위별 항목 표 3개(torso 22·arm 4·leg 9행; measure_code·korean_name·measure_type·basis·iso_clause)
# 실행: .venv/bin/python db/예시_코드/3d/1_기본/01_치수항목_부위별_목록.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 정의된 부위 이름 목록 (겹치지 않게 DISTINCT)
def body_parts():
    sql = """
        SELECT DISTINCT d.body_part
        FROM ref.measure_definitions AS d
        ORDER BY d.body_part
    """
    parts = []
    for row in query(sql):
        parts.append(row["body_part"])
    return parts


# 목적: 부위 하나의 치수 항목 목록 (신체 basis = body 먼저, 옷 basis = garment 다음)
def measure_definitions(body_part="torso"):
    sql = """
        SELECT d.measure_code, d.korean_name, d.measure_type, d.basis, d.iso_clause
        FROM ref.measure_definitions AS d
        WHERE d.body_part = %s
        ORDER BY d.basis, d.measure_code
    """
    return query(sql, (body_part,))


if __name__ == "__main__":
    parts = body_parts()
    print("부위 목록:", parts)
    show("ref.measure_definitions (body_part = torso)", measure_definitions("torso"))
    show("ref.measure_definitions (body_part = arm)", measure_definitions("arm"))
    show("ref.measure_definitions (body_part = leg)", measure_definitions("leg"))
