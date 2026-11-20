# 목적: "회원 탈퇴" — 한 회원의 자세 → 치수 → 신체 정보 → 회원 순서(FK 자식 먼저)로 DELETE 하고, 예시는 rollback 으로 전부 되살림
# 누가 쓰나: 프론트
# 난이도: 고급 — 표 4개에 이어서 DELETE(서브쿼리로 대상 고르기) + 단계마다 행 수 확인 + rollback 후 복구 확인
# 출력: user01 탈퇴 전 행 수, 단계별 DELETE 4행, 탈퇴 후 모두 0 → 되돌림 (rollback) 뒤 행 수 원래대로
# 실행: .venv/bin/python db/예시_코드/front/3_고급/04_회원탈퇴_삭제후_되돌리기.py   (commit=False → DB 는 그대로)
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import connect, query, query_in, show

# 한 회원의 표별 행 수 (connect 하나에서 읽으면 commit 전 상태, query 로 읽으면 저장된 상태)
COUNT_SQL = """
    SELECT
      (SELECT COUNT(*) FROM body.users AS u WHERE u.email = %s) AS users,
      (SELECT COUNT(*) FROM body.profiles AS p JOIN body.users AS u ON u.user_id = p.user_id
        WHERE u.email = %s) AS profiles,
      (SELECT COUNT(*) FROM body.measures AS m JOIN body.profiles AS p ON p.profile_id = m.profile_id
        JOIN body.users AS u ON u.user_id = p.user_id WHERE u.email = %s) AS measures,
      (SELECT COUNT(*) FROM body.poses AS po JOIN body.profiles AS p ON p.profile_id = po.profile_id
        JOIN body.users AS u ON u.user_id = p.user_id WHERE u.email = %s) AS poses
"""

# FK 때문에 자식 표부터 지움: poses·measures → profiles → users
DELETE_STEPS = [
    ("body.poses", """DELETE FROM body.poses WHERE profile_id IN
        (SELECT profile_id FROM (SELECT p.profile_id FROM body.profiles AS p JOIN body.users AS u
         ON u.user_id = p.user_id WHERE u.email = %s) AS t)"""),
    ("body.measures", """DELETE FROM body.measures WHERE profile_id IN
        (SELECT profile_id FROM (SELECT p.profile_id FROM body.profiles AS p JOIN body.users AS u
         ON u.user_id = p.user_id WHERE u.email = %s) AS t)"""),
    ("body.profiles", """DELETE FROM body.profiles WHERE user_id IN
        (SELECT user_id FROM (SELECT u.user_id FROM body.users AS u WHERE u.email = %s) AS t)"""),
    ("body.users", "DELETE FROM body.users WHERE email = %s"),
]


# 목적: email 하나로 COUNT_SQL 의 %s 4개 채우기
def count_params(email):
    return (email, email, email, email)


# 목적: 탈퇴 본체. 단계마다 지운 행 수를 모아 돌려줌. commit=False 면 끝에 rollback
def withdraw(email, commit=True):
    conn = connect()
    steps = []
    try:
        show("탈퇴 전 행 수 (" + email + ")", query_in(conn, COUNT_SQL, count_params(email)))
        for table, sql in DELETE_STEPS:
            with conn.cursor() as cur:
                deleted = cur.execute(sql, (email,))
            steps.append({"step": len(steps) + 1, "table": table, "deleted_rows": deleted})
        show("단계별 DELETE", steps)
        show("탈퇴 후 행 수 (같은 접속, commit 전 — 모두 0)", query_in(conn, COUNT_SQL, count_params(email)))
        if commit:
            conn.commit()
            print("\n  → 저장함 (commit): 탈퇴 완료")
        else:
            conn.rollback()
            print("\n  → 되돌림 (rollback): commit=False 라 아무것도 지워지지 않음")
    except Exception:
        conn.rollback()
        print("\n  → 오류로 되돌림 (rollback)")
        raise
    finally:
        conn.close()
    return {"email": email, "steps": len(steps), "committed": commit}


if __name__ == "__main__":
    # user01 은 자세(poses)까지 있어 4개 표가 모두 지워지는 예
    result = withdraw("user01@example.com", commit=False)
    print("  결과:", result)
    show("rollback 뒤 새 접속으로 다시 센 행 수 (탈퇴 전과 같아야 함)",
         query(COUNT_SQL, count_params("user01@example.com")))
