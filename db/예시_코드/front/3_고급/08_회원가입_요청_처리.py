# 목적: 회원가입 API — 요청(dict) → 입력 검사 → email 중복 확인 → 회원 + 첫 신체 정보(body_type 계산) INSERT → 응답(JSON), 예시는 rollback
# 누가 쓰나: 프론트 (치수까지 한 번에 저장하는 흐름은 front/3_고급/05_사용자_신체정보_저장.py)
# 난이도: 고급 — 한 트랜잭션에서 SELECT 확인 → INSERT 2개, 동시 가입 대비 UNIQUE 위반(IntegrityError)도 응답으로 바꾸기
# 출력: 가입 요청·응답 JSON: 새 email ok true·BMI 20.7·committed false(되돌림 (rollback)), 중복 email·틀린 입력 errors
# 실행: .venv/bin/python db/예시_코드/front/3_고급/08_회원가입_요청_처리.py   (commit=False → DB 는 그대로)
# 참고: 되돌려도 AUTO_INCREMENT 번호는 MySQL 특성상 돌아가지 않음 (행은 남지 않음)
import datetime
import json
import sys
from pathlib import Path

import pymysql

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import connect, execute, query_in
from _body_type import bmi_of, body_type_of, body_type_name
from _검증 import validate


# 목적: 생년월일('1995-03-01') → 오늘 기준 만 나이
def age_from_birth(birth_date):
    born = datetime.date.fromisoformat(str(birth_date))
    today = datetime.date.today()
    age = today.year - born.year
    if (today.month, today.day) < (born.month, born.day):
        age -= 1
    return age


# 목적: API 본체: 가입 요청 → 응답 dict. commit=False 면 INSERT 를 확인만 하고 rollback
def handle_signup(request, commit=True):
    errors = validate(request, need_account=True)
    if len(errors) > 0:
        return {"ok": False, "errors": errors}

    email = str(request["email"]).strip()
    height_cm = float(request["height_cm"])
    weight_kg = float(request["weight_kg"])
    body_type = body_type_of(height_cm, weight_kg)

    conn = connect()
    try:
        used = query_in(conn, "SELECT COUNT(*) AS tally FROM body.users WHERE email = %s", (email,))
        if used[0]["tally"] > 0:
            return {"ok": False, "errors": ["email: 이미 가입한 email (" + email + ")"]}

        user_id = execute(conn, "INSERT INTO body.users (user_name, gender, birth_date, email) VALUES (%s, %s, %s, %s)",
                          (request["user_name"], request["gender"], request["birth_date"], email))
        profile_id = execute(conn, """
            INSERT INTO body.profiles (user_id, gender, age, height_cm, weight_kg, muscle_kg, body_fat_pct, body_type, source_name)
            VALUES (%s, %s, %s, %s, %s, NULL, NULL, %s, 'user')
        """, (user_id, request["gender"], age_from_birth(request["birth_date"]), height_cm, weight_kg, body_type))

        saved = query_in(conn, """
            SELECT u.user_id, p.profile_id, p.body_type
            FROM body.users AS u JOIN body.profiles AS p ON p.user_id = u.user_id
            WHERE u.user_id = %s
        """, (user_id,))
        if commit:
            conn.commit()
        else:
            conn.rollback()
    except pymysql.err.IntegrityError as error:
        # 확인과 INSERT 사이에 다른 사람이 같은 email 로 가입한 경우 (UNIQUE 가 막음)
        conn.rollback()
        return {"ok": False, "errors": ["email: 방금 다른 가입이 먼저 저장됨 (" + str(error.args[0]) + ")"]}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    message = "가입 완료"
    if not commit:
        message = "확인만 함 (commit=False 라 rollback, 저장 안 됨)"
    return {"ok": True, "user_id": user_id, "profile_id": profile_id,
            "body_type": body_type, "body_type_name": body_type_name(body_type),
            "bmi": round(bmi_of(height_cm, weight_kg), 1), "saved_check": saved[0],
            "committed": commit, "message": message}


# 목적: 요청·응답을 JSON 글자로 출력 (한글 그대로)
def print_json(title, data):
    print()
    print("■ " + title)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    new_request = {"user_name": "가입예시", "email": "signup_demo@example.com", "gender": "female",
                   "birth_date": "2000-05-20", "height_cm": 163.0, "weight_kg": 55.0}
    print_json("요청 1 (새 email)", new_request)
    print_json("응답 1", handle_signup(new_request, commit=False))

    dup_request = {"user_name": "중복", "email": "user01@example.com", "gender": "male",
                   "birth_date": "1995-03-14", "height_cm": 172.2, "weight_kg": 62.5}
    print_json("응답 2 (이미 있는 user01@example.com)", handle_signup(dup_request, commit=False))

    bad_request = {"user_name": "", "email": "bad@", "gender": "male", "birth_date": "2020-01-01",
                   "height_cm": 300, "weight_kg": 55.0}
    print_json("응답 3 (틀린 입력, DB 접속 안 함)", handle_signup(bad_request, commit=False))
