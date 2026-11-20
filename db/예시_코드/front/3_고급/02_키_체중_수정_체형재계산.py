# 목적: "키·체중 수정" 저장 — 최근 신체 정보의 키·체중을 UPDATE 하면서 body_type 을 BMI 로 다시 계산해 같이 바꾸기, 예시는 rollback
# 누가 쓰나: 프론트 (새 이력 행으로 저장하는 흐름은 front/3_고급/05_사용자_신체정보_저장.py)
# 난이도: 고급 — 트랜잭션 UPDATE + 파이썬 계산(_body_type)과 SQL CASE 계산이 같은지 대조 + rollback
# 출력: profile 18 체중 62.5→75.0, body_type normal→obese_1(파이썬=SQL True) → 되돌림 (rollback) 뒤 원래 값
# 실행: .venv/bin/python db/예시_코드/front/3_고급/02_키_체중_수정_체형재계산.py   (commit=False → DB 는 그대로)
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import connect, query, query_in, show
from _body_type import bmi_of, body_type_of, body_type_name
from _검증 import HEIGHT_MIN, HEIGHT_MAX, WEIGHT_MIN, WEIGHT_MAX, check_number

# 저장된 행 + SQL 로 다시 계산한 BMI·체형 (db/query/user/02_insert_profile.sql 의 CASE 와 같은 경계)
CHECK_SQL = """
    SELECT p.profile_id, p.height_cm, p.weight_kg, p.body_type,
           ROUND(p.weight_kg / POW(p.height_cm / 100, 2), 1) AS bmi_sql,
           CASE
             WHEN p.weight_kg / POW(p.height_cm / 100, 2) < 18.5 THEN 'underweight'
             WHEN p.weight_kg / POW(p.height_cm / 100, 2) < 23   THEN 'normal'
             WHEN p.weight_kg / POW(p.height_cm / 100, 2) < 25   THEN 'pre_obese'
             WHEN p.weight_kg / POW(p.height_cm / 100, 2) < 30   THEN 'obese_1'
             WHEN p.weight_kg / POW(p.height_cm / 100, 2) < 35   THEN 'obese_2'
             ELSE 'obese_3'
           END AS body_type_sql
    FROM body.profiles AS p
    WHERE p.profile_id = %s
"""


# 목적: 열린 접속에서 email → 가장 최근 profile_id (없으면 None)
def latest_profile_id(conn, email):
    sql = """
        SELECT p.profile_id
        FROM body.users AS u
        JOIN body.profiles AS p ON p.user_id = u.user_id
        WHERE u.email = %s
        ORDER BY p.created_at DESC, p.profile_id DESC
        LIMIT 1
    """
    rows = query_in(conn, sql, (email,))
    if len(rows) == 0:
        return None
    return rows[0]["profile_id"]


# 목적: 키·체중 수정 본체. 체형은 사용자가 고르지 않고 새 키·체중으로 계산해서 같은 UPDATE 에 넣음
def update_height_weight(email, height_cm, weight_kg, commit=True):
    errors = []
    check_number(errors, "height_cm", height_cm, HEIGHT_MIN, HEIGHT_MAX)
    check_number(errors, "weight_kg", weight_kg, WEIGHT_MIN, WEIGHT_MAX)
    if len(errors) > 0:
        raise ValueError("입력 오류: " + " / ".join(errors))
    new_type = body_type_of(height_cm, weight_kg)

    conn = connect()
    try:
        profile_id = latest_profile_id(conn, email)
        if profile_id is None:
            raise ValueError("신체 정보가 없는 email: " + email)
        before = query_in(conn, CHECK_SQL, (profile_id,))
        with conn.cursor() as cur:
            cur.execute("UPDATE body.profiles SET height_cm = %s, weight_kg = %s, body_type = %s WHERE profile_id = %s",
                        (height_cm, weight_kg, new_type, profile_id))
        after = query_in(conn, CHECK_SQL, (profile_id,))
        show("수정 전 (profile_id = " + str(profile_id) + ")", before)
        show("수정 후 (같은 접속, commit 전) — body_type 과 body_type_sql 이 같아야 함", after)
        print("  파이썬 계산: BMI " + str(round(bmi_of(height_cm, weight_kg), 1)) + " → " + new_type
              + " (" + body_type_name(new_type) + ")")
        same = after[0]["body_type"] == after[0]["body_type_sql"]
        print("  파이썬 계산 = SQL CASE 계산:", same)
        if commit:
            conn.commit()
            print("\n  → 저장함 (commit)")
        else:
            conn.rollback()
            print("\n  → 되돌림 (rollback): commit=False 라 DB 에 저장하지 않음")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {"profile_id": profile_id, "body_type": new_type, "committed": commit}


if __name__ == "__main__":
    # user01: 172.2cm 62.5kg(정상) → 체중 75.0kg 로 고치면 BMI 25.3 → 1단계 비만
    result = update_height_weight("user01@example.com", 172.2, 75.0, commit=False)
    print("  결과:", result)
    show("rollback 뒤 새 접속으로 다시 읽기 (62.5kg, normal 이어야 함)", query(CHECK_SQL, (result["profile_id"],)))
