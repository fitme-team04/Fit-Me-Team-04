# 목적: 가입·입력 화면 저장 — 회원(users) → 신체 정보(profiles) → 신체 치수(measures) 를 한 번에 저장
# 누가 쓰나: 프론트
# 난이도: 고급 — 표 3개에 이어서 쓰기(upsert·insert) + 한 트랜잭션 commit / rollback
# 출력: 새 회원 저장 결과 body.users 1행·profiles 1행·measures 3행(estimated) → 되돌림 (rollback), DB 변화 없음
# db/query/user/01_upsert_user.sql · 02_insert_profile.sql · 03_upsert_measure.sql 과 같은 SQL
# 실행: .venv/bin/python db/예시_코드/front/3_고급/05_사용자_신체정보_저장.py   (예시는 commit=False → 끝에 되돌려서 DB 가 바뀌지 않음)
# 참고: 되돌려도 AUTO_INCREMENT 번호는 MySQL 특성상 돌아가지 않음 (행은 남지 않음)
import datetime
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import connect, execute, execute_many, query_in, show
from _body_type import body_type_of                  # 키·체중 → 체형 (대한비만학회 BMI 단계)
from _추정 import MODEL_VERSION                       # 추정 모델 이름 (예시_코드/_추정.py)
from _검증 import validate                            # 입력 검사 (예시_코드/_검증.py)


# 목적: 생년월일('1995-03-01') → 오늘 기준 만 나이
def age_from_birth(birth_date):
    born = datetime.date.fromisoformat(str(birth_date))
    today = datetime.date.today()
    age = today.year - born.year
    if (today.month, today.day) < (born.month, born.day):
        age -= 1
    return age


# 목적: 01: 회원 등록·수정 (email 이 같으면 이름·성별·생년월일 수정) → user_id
def upsert_user(conn, user_name, email, gender, birth_date):
    sql = """
        INSERT INTO body.users (user_name, gender, birth_date, email)
        VALUES (%s, %s, %s, %s) AS new
        ON DUPLICATE KEY UPDATE user_name = new.user_name, gender = new.gender, birth_date = new.birth_date
    """
    execute(conn, sql, (user_name, gender, birth_date, email))
    rows = query_in(conn, "SELECT user_id FROM body.users WHERE email = %s", (email,))
    return rows[0]["user_id"]


# 목적: 02: 신체 정보 한 행 추가 (입력할 때마다 새 행 = 이력, source_name = 'user') → profile_id
# body_type(체형)은 사용자가 고르지 않고 키·체중으로 계산해서 넣음 (_body_type.py)
def insert_profile(conn, user_id, gender, age, height_cm, weight_kg):
    body_type = body_type_of(height_cm, weight_kg)
    sql = """
        INSERT INTO body.profiles (user_id, gender, age, height_cm, weight_kg, muscle_kg, body_fat_pct, body_type, source_name)
        VALUES (%s, %s, %s, %s, %s, NULL, NULL, %s, 'user')
    """
    return execute(conn, sql, (user_id, gender, age, height_cm, weight_kg, body_type))


# 목적: 03: 신체 치수 여러 개 추가·수정. measures = {measure_code: value_cm}
def upsert_measures(conn, profile_id, measures, method, model_version):
    sql = """
        INSERT INTO body.measures (profile_id, measure_code, value_cm, measure_method, model_version)
        VALUES (%s, %s, %s, %s, %s) AS new
        ON DUPLICATE KEY UPDATE value_cm = new.value_cm, measure_method = new.measure_method,
                                model_version = new.model_version
    """
    rows = []
    for code in measures:
        rows.append((profile_id, code, measures[code], method, model_version))
    if len(rows) == 0:
        return 0
    return execute_many(conn, sql, rows)


# 목적: 등록 본체. method 는 'measured'(실측) 또는 'estimated'(추정, model_version 기록)
# commit=False 면 끝에 rollback → 저장하지 않고 결과만 보여 줌
def register(user_name, email, gender, birth_date, height_cm, weight_kg, measures, method,
             commit=True, model_version=None):
    if method not in ("measured", "estimated"):
        raise ValueError("method 는 'measured' 또는 'estimated' 여야 함: " + str(method))

    # 저장 전에 입력 검사 (_검증.py). 틀린 곳이 있으면 DB 에 접속하지 않고 멈춤
    form = {"user_name": user_name, "email": email, "gender": gender, "birth_date": birth_date,
            "height_cm": height_cm, "weight_kg": weight_kg, "measures": measures}
    errors = validate(form, need_account=True)
    if len(errors) > 0:
        raise ValueError("입력 오류: " + " / ".join(errors))
    if method == "measured":
        model_version = None
    if method == "estimated" and model_version is None:
        model_version = MODEL_VERSION

    conn = connect()
    try:
        user_id = upsert_user(conn, user_name, email, gender, birth_date)
        age = age_from_birth(birth_date)
        profile_id = insert_profile(conn, user_id, gender, age, height_cm, weight_kg)
        upsert_measures(conn, profile_id, measures, method, model_version)

        # 저장(또는 되돌리기) 전에 같은 접속에서 방금 넣은 행 확인
        show("body.users (email = " + email + ")", query_in(conn,
             "SELECT user_id, user_name, gender, birth_date, email FROM body.users WHERE email = %s", (email,)))
        show("body.profiles (profile_id = " + str(profile_id) + ")", query_in(conn,
             "SELECT profile_id, user_id, gender, age, height_cm, weight_kg, body_type, source_name FROM body.profiles WHERE profile_id = %s",
             (profile_id,)))
        show("body.measures (profile_id = " + str(profile_id) + ")", query_in(conn,
             "SELECT measure_code, value_cm, measure_method, model_version FROM body.measures WHERE profile_id = %s ORDER BY measure_code",
             (profile_id,)))

        if commit:
            conn.commit()
            print("\n  → 저장함 (commit)")
        else:
            conn.rollback()
            print("\n  → 되돌림 (rollback): commit=False 라 DB 에 저장하지 않음")
    except Exception:
        conn.rollback()
        print("\n  → 오류로 되돌림 (rollback)")
        raise
    finally:
        conn.close()
    return {"user_id": user_id, "profile_id": profile_id, "committed": commit}


if __name__ == "__main__":
    # 예시: 새 회원 + 추정 치수 저장 흐름. commit=False 라 실행해도 DB 는 그대로
    result = register(
        user_name="예시등록",
        email="register_demo@example.com",
        gender="male",
        birth_date="1995-03-01",
        height_cm=175.0,
        weight_kg=75.0,
        measures={"chest_girth": 98.0, "waist_girth": 84.0, "shoulder_width": 44.0},
        method="estimated",
        commit=False,
    )
    print("  결과:", result)
