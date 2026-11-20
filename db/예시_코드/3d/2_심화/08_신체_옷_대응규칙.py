# 목적: 신체 치수 ↔ 옷 실측 치수 대응 규칙(ref.measure_maps)에 양쪽 한글 이름·부위 붙이기 (3D 몸 둘레 → 옷 패턴 폭 연결)
# 누가 쓰나: 3D
# 난이도: 심화 — 같은 정의 표를 역할 이름 2개(bd·gd)로 JOIN = 3개 표 + GROUP BY 집계
# 출력: 신체↔옷 대응 규칙 표 3개 — 전부(8행)·다리만(3행)·부위×factor별 규칙 수(5행); body/garment_measure_code·factor
# 실행: .venv/bin/python db/예시_코드/3d/2_심화/08_신체_옷_대응규칙.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 대응 규칙 전부 (신체값 ≈ 옷값 × factor). body_part 를 주면 그 부위만
def measure_maps(body_part=None):
    sql = """
        SELECT bd.body_part,
               mm.body_measure_code, bd.korean_name AS body_name, bd.measure_type AS body_type,
               mm.garment_measure_code, gd.korean_name AS garment_name, gd.measure_type AS garment_type,
               mm.factor
        FROM ref.measure_maps AS mm
        JOIN ref.measure_definitions AS bd ON bd.measure_code = mm.body_measure_code
        JOIN ref.measure_definitions AS gd ON gd.measure_code = mm.garment_measure_code
        WHERE (%s IS NULL OR bd.body_part = %s)
        ORDER BY bd.body_part, mm.body_measure_code
    """
    return query(sql, (body_part, body_part))


# 목적: 부위 × factor 별 규칙 수 (factor 2 = 단면 → 둘레, factor 1 = 길이 그대로)
def map_tally_by_part():
    sql = """
        SELECT bd.body_part, mm.factor, COUNT(*) AS map_tally,
               GROUP_CONCAT(gd.measure_code ORDER BY gd.measure_code SEPARATOR ', ') AS garment_codes
        FROM ref.measure_maps AS mm
        JOIN ref.measure_definitions AS bd ON bd.measure_code = mm.body_measure_code
        JOIN ref.measure_definitions AS gd ON gd.measure_code = mm.garment_measure_code
        GROUP BY bd.body_part, mm.factor
        ORDER BY bd.body_part, mm.factor
    """
    return query(sql)


if __name__ == "__main__":
    show("신체 ↔ 옷 대응 규칙 전부", measure_maps())
    show("대응 규칙 (다리만)", measure_maps("leg"))
    show("부위 × factor 별 규칙 수", map_tally_by_part())
