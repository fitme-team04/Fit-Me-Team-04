# 목적: 사람마다 같은 성별 평균에서 키·체중이 얼마나 떨어져 있는지 (차이 cm·kg + 표준점수 z), 평균에서 가장 먼 사람
# 누가 쓰나: 공통 (AI 이상값 찾기, 3D 평균 몸 / 극단 몸 고르기)
# 난이도: 고급 — 창 함수 AVG·STDDEV_POP OVER (PARTITION BY gender) + 파생 테이블에서 z = (값 − 평균) / 표준편차 + ABS 정렬
# 출력: 표 3개 — 여성·남성 성별 평균과의 키·체중 차이·표준점수 z(각 11행), 평균에서 가장 먼 사람(5행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/3_고급/04_성별_평균_편차.py
# z 가 0 이면 평균, ±1 이면 표준편차 1개만큼 떨어짐. 순위·백분위는 03_성별_키_순위.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show

# 키·체중 편차 계산 SQL (아래 두 함수가 같이 씀). GROUP BY 없이 창 함수라 사람 행이 그대로 남음
DEVIATION_SQL = """
    SELECT t.profile_id, t.gender, t.source_name, t.height_cm, t.weight_kg,
           ROUND(t.height_cm - t.avg_height, 1) AS height_diff_cm,
           ROUND((t.height_cm - t.avg_height) / t.sd_height, 2) AS height_z,
           ROUND(t.weight_kg - t.avg_weight, 1) AS weight_diff_kg,
           ROUND((t.weight_kg - t.avg_weight) / t.sd_weight, 2) AS weight_z
    FROM (
        SELECT p.profile_id, p.gender, p.source_name, p.height_cm, p.weight_kg,
               AVG(p.height_cm)        OVER (PARTITION BY p.gender) AS avg_height,
               STDDEV_POP(p.height_cm) OVER (PARTITION BY p.gender) AS sd_height,
               AVG(p.weight_kg)        OVER (PARTITION BY p.gender) AS avg_weight,
               STDDEV_POP(p.weight_kg) OVER (PARTITION BY p.gender) AS sd_weight
        FROM body.profiles AS p
        WHERE p.height_cm IS NOT NULL
          AND p.weight_kg IS NOT NULL
    ) AS t
"""


# 목적: 성별 하나의 사람마다 키·체중 편차 (키 큰 순)
def deviations(gender="female"):
    sql = DEVIATION_SQL + """
    WHERE t.gender = %s
    ORDER BY t.height_cm DESC
    """
    return query(sql, (gender,))


# 목적: 성별 평균에서 키·체중 z 를 합쳐 가장 먼 사람 앞 limit 명 (|키 z| + |체중 z| 큰 순)
def farthest_from_average(limit=5):
    sql = """
        SELECT d.*, ROUND(ABS(d.height_z) + ABS(d.weight_z), 2) AS total_distance
        FROM (""" + DEVIATION_SQL + """) AS d
        ORDER BY total_distance DESC
        LIMIT %s
    """
    return query(sql, (limit,))


if __name__ == "__main__":
    show("여성: 성별 평균과의 차이·표준점수", deviations("female"))
    show("남성: 성별 평균과의 차이·표준점수", deviations("male"))
    show("성별 평균에서 가장 먼 사람 5명", farthest_from_average(5))
