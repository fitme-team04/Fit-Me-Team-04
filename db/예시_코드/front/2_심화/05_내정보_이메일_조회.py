# 목적: 로그인 후 "내 정보" 화면 — email 로 사용자 한 명 + 가장 최근 신체 정보 + 저장된 치수 개수
# 누가 쓰나: 프론트 (사용자 목록은 공통/사람/1_기본/01_사용자_목록.py)
# 난이도: 심화 — 2~3개 표 LEFT JOIN (신체 정보·치수가 없어도 사용자는 나옴) + GROUP BY COUNT
# 출력: user01 의 내 정보 1행·신체 정보 이력 1행(measure_tally), 없는 email 은 0행 '(결과 없음)'
# 실행: .venv/bin/python db/예시_코드/front/2_심화/05_내정보_이메일_조회.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: email 로 사용자 한 명 + 그 사람의 가장 최근 신체 정보 (내 정보 화면)
def user_by_email(email):
    sql = """
        SELECT u.user_id, u.user_name, u.gender, u.email,
               p.profile_id, p.height_cm, p.weight_kg, p.body_type, p.created_at AS profile_created_at
        FROM body.users AS u
        LEFT JOIN body.profiles AS p ON p.user_id = u.user_id
        WHERE u.email = %s
        ORDER BY p.created_at DESC, p.profile_id DESC
        LIMIT 1
    """
    return query(sql, (email,))


# 목적: email 로 그 사람의 신체 정보 이력(입력할 때마다 한 행)과 신체 정보마다 저장된 치수 개수
def profile_history(email):
    sql = """
        SELECT p.profile_id, p.created_at, p.height_cm, p.weight_kg,
               COUNT(m.measure_code) AS measure_tally
        FROM body.users AS u
        JOIN body.profiles AS p ON p.user_id = u.user_id
        LEFT JOIN body.measures AS m ON m.profile_id = p.profile_id
        WHERE u.email = %s
        GROUP BY p.profile_id, p.created_at, p.height_cm, p.weight_kg
        ORDER BY p.created_at DESC, p.profile_id DESC
    """
    return query(sql, (email,))


if __name__ == "__main__":
    show("내 정보 (email = user01@example.com)", user_by_email("user01@example.com"))
    show("신체 정보 이력 (email = user01@example.com)", profile_history("user01@example.com"))
    show("없는 email (email = nobody@example.com)", user_by_email("nobody@example.com"))
