# 목적: 가입한 사용자 목록 보기 — 전체(앞 몇 명), 성별로 거르기 (관리 화면)
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 기본 — 표 1개(body.users) SELECT + WHERE·ORDER BY·LIMIT
# 출력: 표 2개 — body.users 앞 10명(user_id·이름·성별·생일·나이·이메일·가입일, 5행), 여성 사용자(2행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/1_기본/01_사용자_목록.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 사용자 목록 (지금 나이는 birth_date 로 계산)
def users(limit=10):
    sql = """
        SELECT u.user_id, u.user_name, u.gender, u.birth_date,
               TIMESTAMPDIFF(YEAR, u.birth_date, CURDATE()) AS age_now,
               u.email, u.created_at
        FROM body.users AS u
        ORDER BY u.user_id
        LIMIT %s
    """
    return query(sql, (limit,))


# 목적: 성별(male / female) 하나의 사용자
def users_by_gender(gender="female"):
    sql = """
        SELECT u.user_id, u.user_name, u.birth_date, u.email
        FROM body.users AS u
        WHERE u.gender = %s
        ORDER BY u.user_id
    """
    return query(sql, (gender,))


if __name__ == "__main__":
    show("body.users (앞 10명)", users(10))
    show("여성 사용자 (gender = female)", users_by_gender("female"))
