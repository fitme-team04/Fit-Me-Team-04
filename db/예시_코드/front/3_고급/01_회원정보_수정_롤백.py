# 목적: "회원 정보 수정" 저장 버튼 — email 로 찾은 회원의 이름·생년월일을 한 트랜잭션에서 UPDATE, 예시는 rollback 으로 되돌림
# 누가 쓰나: 프론트
# 난이도: 고급 — 트랜잭션 쓰기(UPDATE) + 같은 접속에서 바뀐 값 확인 + rollback 후 새 접속으로 원래 값 확인
# 출력: user01 이름·생년월일 수정 전/후 1행씩 → 되돌림 (rollback) 뒤 원래 값 재조회, 틀린 입력은 DB 전에 오류
# 실행: .venv/bin/python db/예시_코드/front/3_고급/01_회원정보_수정_롤백.py   (commit=False → DB 는 그대로)
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import connect, query, query_in, show
from _검증 import is_empty, check_birth_date          # 생년월일 형식·나이 범위 검사

USER_SQL = "SELECT user_id, user_name, birth_date, email, updated_at FROM body.users WHERE email = %s"


# 목적: 열린 접속에서 SQL 한 개 실행 → 영향받은 행 수 (UPDATE·DELETE 가 몇 행을 바꿨는지)
def run(conn, sql, params):
    with conn.cursor() as cur:
        changed = cur.execute(sql, params)
    return changed


# 목적: 수정 값 검사 → 틀린 곳 목록 (이름 1~50자, 생년월일 YYYY-MM-DD·나이 범위)
def check_edit(user_name, birth_date):
    errors = []
    if is_empty(user_name):
        errors.append("user_name: 값이 없음")
    elif len(str(user_name)) > 50:
        errors.append("user_name: 50자 이하")
    check_birth_date(errors, birth_date)
    return errors


# 목적: 회원 정보 수정 본체. commit=False 면 바꾼 뒤 확인만 하고 rollback
def update_user(email, user_name, birth_date, commit=True):
    errors = check_edit(user_name, birth_date)
    if len(errors) > 0:
        raise ValueError("입력 오류: " + " / ".join(errors))

    conn = connect()
    try:
        show("수정 전 (같은 접속)", query_in(conn, USER_SQL, (email,)))
        changed = run(conn, "UPDATE body.users SET user_name = %s, birth_date = %s WHERE email = %s",
                      (user_name, birth_date, email))
        if changed == 0:
            raise ValueError("없는 email 이거나 값이 같아 바뀐 행 없음: " + email)
        show("수정 후 (같은 접속, 아직 commit 전)", query_in(conn, USER_SQL, (email,)))
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
    return {"email": email, "changed_rows": changed, "committed": commit}


if __name__ == "__main__":
    result = update_user("user01@example.com", "이름바꾼사용자01", "1995-04-01", commit=False)
    print("  결과:", result)
    show("rollback 뒤 새 접속으로 다시 읽기 (원래 값이어야 함)", query(USER_SQL, ("user01@example.com",)))

    try:
        update_user("user01@example.com", "", "1995/04/01", commit=False)
    except ValueError as error:
        print("\n■ 틀린 입력 → DB 접속 전에 멈춤:", error)
