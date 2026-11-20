# 목적: 신체 치수 항목마다 표본 수·최소·평균·최대 → 3D 몸 모델 슬라이더(최소~최대, 처음 값 = 평균) 범위
# 누가 쓰나: 3D
# 난이도: 심화 — 2개 표 JOIN(body.measures + ref.measure_definitions) + GROUP BY + COUNT·MIN·AVG·MAX
# 출력: 슬라이더 범위 표 — 전체 부위(23행)·팔만(3행); measure_code·samples·slider_min·slider_default·slider_max
# 실행: .venv/bin/python db/예시_코드/3d/2_심화/04_치수별_슬라이더_범위.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 부위 하나(None 이면 전부)의 치수별 슬라이더 범위
def slider_ranges(body_part=None):
    sql = """
        SELECT d.body_part, m.measure_code, d.korean_name,
               COUNT(*) AS samples,
               MIN(m.value_cm) AS slider_min,
               ROUND(AVG(m.value_cm), 1) AS slider_default,
               MAX(m.value_cm) AS slider_max
        FROM body.measures AS m
        JOIN ref.measure_definitions AS d ON d.measure_code = m.measure_code
        WHERE (%s IS NULL OR d.body_part = %s)
        GROUP BY d.body_part, m.measure_code, d.korean_name
        ORDER BY FIELD(d.body_part, 'full', 'torso', 'arm', 'leg', 'neck'), m.measure_code
    """
    return query(sql, (body_part, body_part))


if __name__ == "__main__":
    show("슬라이더 범위 (전체 부위)", slider_ranges())
    show("슬라이더 범위 (팔만)", slider_ranges("arm"))
