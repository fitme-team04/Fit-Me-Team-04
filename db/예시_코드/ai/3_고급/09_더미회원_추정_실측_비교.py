# 목적: 더미 회원 5명이 키·체중만 입력했다고 치고 k-NN 으로 추정한 치수를 실제 실측값(ANSUR II 23항목)과 회원·부위별로 비교
# 누가 쓰나: AI (서비스 화면에 나갈 추정값이 회원마다 얼마나 틀리는지)
# 난이도: 고급 — 4개 표(users·profiles·measures·measure_definitions) JOIN + CTE + 창 함수(ROW_NUMBER 로 회원별 최신 신체 정보) + 파이썬 k-NN(본인 제외)·오차율
# 출력: 회원 1 치수 22항목 실측·추정·오차 표, 부위별 MAE 4행(torso 5.95cm), 회원 5명 요약(MAE 3.15~8.04cm)
# 실행: .venv/bin/python db/예시_코드/ai/3_고급/09_더미회원_추정_실측_비교.py
# 08 은 실측자 전체의 치수별 평균 오차, 여기는 회원 한 명 한 명의 항목별 오차·가장 틀린 항목
import statistics
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show
from _추정 import candidate_rows, group_by_profile, nearest      # k-NN 재료 (예시_코드/_추정.py)


# 목적: 회원별 가장 최근 신체 정보 1개의 실측 치수 (세로 모양)
def member_actuals():
    sql = """
        WITH latest AS (
            SELECT u.user_id, u.user_name, p.profile_id, p.gender, p.height_cm, p.weight_kg,
                   ROW_NUMBER() OVER (PARTITION BY u.user_id ORDER BY p.created_at DESC, p.profile_id DESC) AS rn
            FROM body.users AS u
            JOIN body.profiles AS p ON p.user_id = u.user_id
        )
        SELECT l.user_id, l.user_name, l.profile_id, l.gender, l.height_cm, l.weight_kg,
               m.measure_code, d.korean_name, d.body_part, m.value_cm
        FROM latest AS l
        JOIN body.measures AS m
          ON m.profile_id = l.profile_id
         AND m.measure_method = 'measured'
        JOIN ref.measure_definitions AS d ON d.measure_code = m.measure_code
        WHERE l.rn = 1
          AND m.measure_code <> 'height'
        ORDER BY l.user_id, d.body_part, m.measure_code
    """
    return query(sql)


# 목적: 세로 행 → 회원별로 묶기 [{"user_id", "user_name", "profile_id", "gender", "height", "weight", "rows": [...]}]
def group_members(rows):
    members = []
    by_id = {}
    for row in rows:
        uid = row["user_id"]
        if uid not in by_id:
            item = {"user_id": uid, "user_name": row["user_name"], "profile_id": row["profile_id"],
                    "gender": row["gender"], "height": float(row["height_cm"]),
                    "weight": float(row["weight_kg"]), "rows": []}
            by_id[uid] = item
            members.append(item)
        by_id[uid]["rows"].append(row)
    return members


# 목적: 회원 본인을 뺀 같은 성별 실측자로 k-NN 추정 → {코드: 추정값}
def estimate_without_self(member, k):
    people = group_by_profile(candidate_rows(member["gender"]))
    others = {}
    for pid in people:
        if pid != member["profile_id"]:
            others[pid] = people[pid]
    neighbors = nearest(others, member["height"], member["weight"], k)
    values_by_code = {}
    for nb in neighbors:
        measures = others[nb["profile_id"]]["measures"]
        for code in measures:
            if code not in values_by_code:
                values_by_code[code] = []
            values_by_code[code].append(measures[code])
    estimate = {}
    for code in values_by_code:
        estimate[code] = statistics.mean(values_by_code[code])
    return estimate


# 목적: 회원 한 명의 항목별 비교 행 (추정할 수 없는 항목은 뺌)
def compare_member(member, k):
    estimate = estimate_without_self(member, k)
    result = []
    for row in member["rows"]:
        code = row["measure_code"]
        if code not in estimate:
            continue
        actual = float(row["value_cm"])
        error = estimate[code] - actual
        result.append({"measure_code": code, "korean_name": row["korean_name"], "body_part": row["body_part"],
                       "actual_cm": actual, "estimated_cm": round(estimate[code], 1),
                       "error_cm": round(error, 1), "abs_pct": round(abs(error) * 100.0 / actual, 1)})
    return result


# 목적: 비교 행 → 부위별 평균 절대 오차
def by_body_part(rows):
    parts = {}
    for row in rows:
        if row["body_part"] not in parts:
            parts[row["body_part"]] = []
        parts[row["body_part"]].append(abs(row["error_cm"]))
    result = []
    for part in sorted(parts):
        result.append({"body_part": part, "n": len(parts[part]), "mae_cm": round(statistics.mean(parts[part]), 2)})
    return result


if __name__ == "__main__":
    k = 3
    members = group_members(member_actuals())
    summary = []
    for member in members:
        rows = compare_member(member, k)
        if member["user_id"] == 1:
            show("회원 1 (" + member["user_name"] + ") 항목별 추정 vs 실측, k = " + str(k), rows)
            show("회원 1 부위별 평균 절대 오차", by_body_part(rows))
        if len(rows) == 0:
            continue
        abs_errors = []
        worst = rows[0]
        for row in rows:
            abs_errors.append(abs(row["error_cm"]))
            if abs(row["error_cm"]) > abs(worst["error_cm"]):
                worst = row
        summary.append({"user_id": member["user_id"], "user_name": member["user_name"], "gender": member["gender"],
                        "compared": len(rows), "mae_cm": round(statistics.mean(abs_errors), 2),
                        "worst_measure": worst["measure_code"], "worst_error_cm": worst["error_cm"]})
    show("회원별 요약 (본인 제외 k-NN)", summary)
