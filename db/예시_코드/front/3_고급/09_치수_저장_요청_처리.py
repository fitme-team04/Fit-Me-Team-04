# 목적: 치수 저장 API — 요청(email·measures) → 형식·범위 검사 → DB 에 있는 신체 치수 코드인지 확인 → 최근 신체 정보에 upsert → 응답(JSON: 추가·수정·그대로 목록), 예시는 rollback
# 누가 쓰나: 프론트 (차이표만 보는 저장 예시는 front/3_고급/03_치수_추가수정_롤백.py)
# 난이도: 고급 — IN (%s, %s, ...) 자리 수를 값 개수만큼 만들기 + 트랜잭션 upsert + 결과 분류 + JSON 응답
# 출력: 치수 저장 응답 JSON: added·updated·unchanged·committed false(되돌림 (rollback)), 틀린 코드·범위·email errors
# 실행: .venv/bin/python db/예시_코드/front/3_고급/09_치수_저장_요청_처리.py   (commit=False → DB 는 그대로)
import json
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import connect, execute_many, query_in
from _검증 import MEASURE_MIN, MEASURE_MAX, check_number, is_empty

UPSERT_SQL = """
    INSERT INTO body.measures (profile_id, measure_code, value_cm, measure_method, model_version)
    VALUES (%s, %s, %s, 'measured', NULL) AS new
    ON DUPLICATE KEY UPDATE value_cm = new.value_cm, measure_method = new.measure_method,
                            model_version = new.model_version
"""


# 목적: 열린 접속에서 codes 중 신체(basis = body) 치수 정의에 있는 코드만 → set. IN 자리(%s)를 개수만큼 만듦
def known_body_codes(conn, codes):
    if len(codes) == 0:
        return set()
    marks = ", ".join(["%s"] * len(codes))
    sql = "SELECT measure_code FROM ref.measure_definitions WHERE basis = 'body' AND measure_code IN (" + marks + ")"
    found = set()
    for row in query_in(conn, sql, tuple(codes)):
        found.add(row["measure_code"])
    return found


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


# 목적: API 본체: 요청 → 응답 dict (ok=False 면 errors)
def handle_save_measures(request, commit=True):
    errors = []
    email = request.get("email")
    measures = request.get("measures")
    if is_empty(email):
        errors.append("email: 값이 없음")
    if measures is None or len(measures) == 0:
        errors.append("measures: 저장할 치수가 없음")
        return {"ok": False, "errors": errors}
    for code in measures:
        check_number(errors, "measures." + str(code), measures[code], MEASURE_MIN, MEASURE_MAX)
    if len(errors) > 0:
        return {"ok": False, "errors": errors}

    conn = connect()
    try:
        codes = list(measures)
        known = known_body_codes(conn, codes)
        for code in codes:
            if code not in known:
                errors.append("measures." + str(code) + ": 신체 치수 코드가 아님")
        if len(errors) > 0:
            return {"ok": False, "errors": errors}

        profile_id = latest_profile_id(conn, email)
        if profile_id is None:
            return {"ok": False, "errors": ["email: 신체 정보가 없음 (" + str(email) + ")"]}

        before = {}
        for row in query_in(conn, "SELECT measure_code, value_cm FROM body.measures WHERE profile_id = %s", (profile_id,)):
            before[row["measure_code"]] = float(row["value_cm"])

        rows = []
        added = []
        updated = []
        unchanged = []
        for code in codes:
            value = float(measures[code])
            rows.append((profile_id, code, value))
            if code not in before:
                added.append(code)
            elif before[code] != value:
                updated.append({"code": code, "before": before[code], "after": value})
            else:
                unchanged.append(code)
        execute_many(conn, UPSERT_SQL, rows)

        if commit:
            conn.commit()
        else:
            conn.rollback()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return {"ok": True, "profile_id": profile_id, "added": added, "updated": updated,
            "unchanged": unchanged, "committed": commit}


# 목적: 요청·응답을 JSON 글자로 출력 (한글 그대로)
def print_json(title, data):
    print()
    print("■ " + title)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    # user02(profile 19): 가슴둘레 100.7 → 101.5 수정, 허리둘레 95.8 그대로, 배둘레 추가
    ok_request = {"email": "user02@example.com",
                  "measures": {"chest_girth": 101.5, "waist_girth": 95.8, "stomach_girth": 98.0}}
    print_json("요청 1", ok_request)
    print_json("응답 1", handle_save_measures(ok_request, commit=False))

    print_json("응답 2 (옷 치수 코드·없는 코드)", handle_save_measures(
        {"email": "user02@example.com", "measures": {"chest_width": 50.0, "unknown_code": 30.0}}, commit=False))
    print_json("응답 3 (범위 밖 값)", handle_save_measures(
        {"email": "user02@example.com", "measures": {"chest_girth": 5.0}}, commit=False))
    print_json("응답 4 (없는 email)", handle_save_measures(
        {"email": "nobody@example.com", "measures": {"chest_girth": 90.0}}, commit=False))
