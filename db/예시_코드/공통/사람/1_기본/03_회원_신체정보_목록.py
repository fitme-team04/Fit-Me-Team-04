# 목적: 회원(user_id 가 있는 사람)이 입력한 신체 정보만 보기 — 데이터셋 행(ansur2·bodym)은 빼고
# 누가 쓰나: 공통 (프론트 회원 관리, 3D 회원 몸 모델)
# 난이도: 기본 — 표 1개(body.profiles) SELECT + WHERE IS NOT NULL·ORDER BY
# 출력: 표 2개 — 회원의 신체 정보(user_id·성별·나이·키·체중·체형·출처, 5행), 회원 2의 신체 정보(1행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/1_기본/03_회원_신체정보_목록.py
# user_id 가 NULL 이면 데이터셋 한 명, 값이 있으면 회원 (db/sql/21_body_profiles.sql 주석)
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 회원의 신체 정보 전부 (user_id 순)
def member_profiles():
    sql = """
        SELECT p.profile_id, p.user_id, p.gender, p.age, p.height_cm, p.weight_kg,
               p.body_type, p.source_name, p.created_at
        FROM body.profiles AS p
        WHERE p.user_id IS NOT NULL
        ORDER BY p.user_id, p.profile_id
    """
    return query(sql)


# 목적: 회원 한 명(user_id)의 신체 정보 (여러 번 입력했으면 최근 것부터)
def profiles_of_user(user_id=2):
    sql = """
        SELECT p.profile_id, p.user_id, p.gender, p.age, p.height_cm, p.weight_kg,
               p.body_type, p.created_at
        FROM body.profiles AS p
        WHERE p.user_id = %s
        ORDER BY p.created_at DESC, p.profile_id DESC
    """
    return query(sql, (user_id,))


if __name__ == "__main__":
    show("회원의 신체 정보 (user_id IS NOT NULL)", member_profiles())
    show("회원 2 의 신체 정보", profiles_of_user(2))
