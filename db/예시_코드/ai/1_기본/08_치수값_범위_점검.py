# 목적: 치수 항목마다 실측값의 최솟값·최댓값·평균을 보고, 입력 허용 범위(_검증.py) 밖 이상값이 있는지 점검
# 누가 쓰나: AI (학습 전 이상값 거르기)
# 난이도: 기본 — 표 1개(body.measures) COUNT·MIN·MAX·AVG + WHERE (GROUP BY 없이 항목마다), 범위 비교는 파이썬
# 출력: 치수 23항목별 n·min·max·avg_cm·허용범위·status 표(범위 밖 0개), hip_girth 최대 3개(123.1cm 등)
# 실행: .venv/bin/python db/예시_코드/ai/1_기본/08_치수값_범위_점검.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show
from _검증 import MEASURE_MIN, MEASURE_MAX, HEIGHT_MIN, HEIGHT_MAX   # 입력 허용 범위 (예시_코드/_검증.py)


# 목적: 실측 치수가 있는 항목 코드 목록
def measured_codes():
    sql = """
        SELECT DISTINCT m.measure_code
        FROM body.measures AS m
        WHERE m.measure_method = 'measured'
        ORDER BY m.measure_code
    """
    codes = []
    for row in query(sql):
        codes.append(row["measure_code"])
    return codes


# 목적: 항목 하나의 실측값 개수·최솟값·최댓값·평균
def value_range(measure_code):
    sql = """
        SELECT COUNT(*) AS n, MIN(m.value_cm) AS min_cm, MAX(m.value_cm) AS max_cm,
               ROUND(AVG(m.value_cm), 1) AS avg_cm
        FROM body.measures AS m
        WHERE m.measure_code = %s
          AND m.measure_method = 'measured'
    """
    return query(sql, (measure_code,))[0]


# 목적: 항목 하나의 허용 범위 (키는 키 범위, 나머지는 치수 범위)
def allowed_range(measure_code):
    if measure_code == "height":
        return HEIGHT_MIN, HEIGHT_MAX
    return MEASURE_MIN, MEASURE_MAX


# 목적: 항목 하나에서 가장 큰 값 몇 개 (이상값 후보 확인)
def largest_values(measure_code, limit=3):
    sql = """
        SELECT m.profile_id, m.value_cm
        FROM body.measures AS m
        WHERE m.measure_code = %s
          AND m.measure_method = 'measured'
        ORDER BY m.value_cm DESC
        LIMIT %s
    """
    return query(sql, (measure_code, limit))


if __name__ == "__main__":
    rows = []
    bad = 0
    for code in measured_codes():
        r = value_range(code)
        low, high = allowed_range(code)
        status = "ok"
        if float(r["min_cm"]) < low or float(r["max_cm"]) > high:
            status = "범위 밖 있음"
            bad += 1
        rows.append({"measure_code": code, "n": r["n"], "min_cm": r["min_cm"], "max_cm": r["max_cm"],
                     "avg_cm": r["avg_cm"], "allowed": str(low) + "~" + str(high), "status": status})
    show("치수 항목별 실측값 범위", rows)
    print("  → 허용 범위 밖 항목:", bad, "개")
    show("hip_girth 가장 큰 값 3개", largest_values("hip_girth", 3))
