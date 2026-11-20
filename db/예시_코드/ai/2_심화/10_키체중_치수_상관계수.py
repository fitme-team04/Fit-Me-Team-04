# 목적: 키(또는 체중)와 치수 항목마다 피어슨 상관계수 r 을 SQL 집계로 계산 → 키·체중으로 예측하기 좋은 치수 고르기
# 누가 쓰나: AI (회귀·k-NN 특징으로 키·체중이 쓸모 있는지 확인)
# 난이도: 심화 — 2개 표 JOIN + GROUP BY 집계식(SUM·COUNT·SQRT 로 상관계수) + HAVING, 한 항목은 파이썬 statistics 로 검산
# 출력: 키↔치수 r 22행(arm_length 0.93 최고)·체중↔치수 r 22행(hip_depth 0.974 최고), statistics 검산 0.189
# r = (nΣxy − ΣxΣy) / √((nΣx² − (Σx)²)(nΣy² − (Σy)²))
# 실행: .venv/bin/python db/예시_코드/ai/2_심화/10_키체중_치수_상관계수.py
import statistics
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show

# x 열마다 SQL 하나씩 (열 이름은 %s 로 넣을 수 없어서 고정 SQL 두 개)
SQL_BY_X = {
    "height_cm": """
        SELECT m.measure_code, COUNT(*) AS n,
               ROUND((COUNT(*) * SUM(p.height_cm * m.value_cm) - SUM(p.height_cm) * SUM(m.value_cm))
                     / SQRT((COUNT(*) * SUM(p.height_cm * p.height_cm) - SUM(p.height_cm) * SUM(p.height_cm))
                          * (COUNT(*) * SUM(m.value_cm * m.value_cm) - SUM(m.value_cm) * SUM(m.value_cm))), 3) AS r
        FROM body.profiles AS p
        JOIN body.measures AS m ON m.profile_id = p.profile_id
        WHERE m.measure_method = 'measured'
          AND m.measure_code <> 'height'
          AND p.height_cm IS NOT NULL
        GROUP BY m.measure_code
        HAVING COUNT(*) >= %s
        ORDER BY ABS(r) DESC
    """,
    "weight_kg": """
        SELECT m.measure_code, COUNT(*) AS n,
               ROUND((COUNT(*) * SUM(p.weight_kg * m.value_cm) - SUM(p.weight_kg) * SUM(m.value_cm))
                     / SQRT((COUNT(*) * SUM(p.weight_kg * p.weight_kg) - SUM(p.weight_kg) * SUM(p.weight_kg))
                          * (COUNT(*) * SUM(m.value_cm * m.value_cm) - SUM(m.value_cm) * SUM(m.value_cm))), 3) AS r
        FROM body.profiles AS p
        JOIN body.measures AS m ON m.profile_id = p.profile_id
        WHERE m.measure_method = 'measured'
          AND m.measure_code <> 'height'
          AND p.weight_kg IS NOT NULL
        GROUP BY m.measure_code
        HAVING COUNT(*) >= %s
        ORDER BY ABS(r) DESC
    """,
}


# 목적: x 열(height_cm / weight_kg)과 치수마다 상관계수 (min_n 명 이상 잰 치수만)
def correlations(x_col, min_n=5):
    return query(SQL_BY_X[x_col], (min_n,))


# 목적: 검산용: 치수 하나의 (키, 값) 짝 → 파이썬 statistics.correlation
def python_r(measure_code):
    sql = """
        SELECT p.height_cm, m.value_cm
        FROM body.profiles AS p
        JOIN body.measures AS m ON m.profile_id = p.profile_id
        WHERE m.measure_code = %s
          AND m.measure_method = 'measured'
          AND p.height_cm IS NOT NULL
    """
    xs = []
    ys = []
    for row in query(sql, (measure_code,)):
        xs.append(float(row["height_cm"]))
        ys.append(float(row["value_cm"]))
    return round(statistics.correlation(xs, ys), 3)


if __name__ == "__main__":
    height_rows = correlations("height_cm", 5)
    show("키 ↔ 치수 상관계수 r (5명 이상)", height_rows)
    show("체중 ↔ 치수 상관계수 r (5명 이상)", correlations("weight_kg", 5))
    print()
    print("  검산 (chest_girth, 키): 파이썬 statistics.correlation =", python_r("chest_girth"))
    print("  ※ |r| 이 1 에 가까울수록 직선 관계가 강함. 예시 DB 는 사람이 적어 값이 흔들림")
