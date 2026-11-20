# 목적: 옷 실측 치수 하나가 정한 범위 안인 사이즈 찾기 (예: 가슴단면 52~55 cm) — "이 정도 품이면 되는" 사이즈 후보
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 기본 — 표 1개(garment.measures) + WHERE ... BETWEEN ... AND ... + ORDER BY
# 출력: 가슴단면 52~55cm 3행, 어깨너비(옷) 45~48cm 3행, 소매길이 긴 순 3행 (size_id·치수코드·value_cm)
# 실행: .venv/bin/python db/예시_코드/공통/옷/1_기본/09_치수값_범위로_찾기.py
# BETWEEN 52 AND 55 는 52 ≤ 값 ≤ 55 (양 끝 포함)
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 옷 실측(basis = garment) 치수 하나가 low_cm ~ high_cm 안인 행
def sizes_in_value_range(measure_code="chest_width", low_cm=52, high_cm=55):
    sql = """
        SELECT gm.size_id, gm.measure_code, gm.value_cm
        FROM garment.measures AS gm
        WHERE gm.measure_code = %s
          AND gm.basis = 'garment'
          AND gm.value_cm BETWEEN %s AND %s
        ORDER BY gm.value_cm, gm.size_id
    """
    return query(sql, (measure_code, low_cm, high_cm))


# 목적: 치수 하나의 옷 실측값을 큰 것부터 (앞 limit 개)
def largest_values(measure_code="sleeve_length", limit=5):
    sql = """
        SELECT gm.size_id, gm.value_cm
        FROM garment.measures AS gm
        WHERE gm.measure_code = %s
          AND gm.basis = 'garment'
        ORDER BY gm.value_cm DESC
        LIMIT %s
    """
    return query(sql, (measure_code, limit))


if __name__ == "__main__":
    show("가슴단면 52~55 cm 인 사이즈 (size_id)", sizes_in_value_range("chest_width", 52, 55))
    show("어깨너비(옷) 45~48 cm 인 사이즈", sizes_in_value_range("garment_shoulder_width", 45, 48))
    show("소매길이 긴 순 (앞 5개)", largest_values("sleeve_length", 5))
