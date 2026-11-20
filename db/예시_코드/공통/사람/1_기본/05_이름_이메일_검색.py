# 목적: 사용자 이름 일부·이메일 도메인으로 사용자 찾기 (관리 화면 검색창)
# 누가 쓰나: 공통 (프론트 관리 화면)
# 난이도: 기본 — 표 1개(body.users) SELECT + WHERE LIKE (앞·뒤 % 패턴)
# 출력: 표 3개 — 이름에 '사용자0' 포함(5행), 이메일 도메인 example.com(5행), 이메일 user03 시작(1행); 열 user_id·이름·이메일
# 실행: .venv/bin/python db/예시_코드/공통/사람/1_기본/05_이름_이메일_검색.py
# LIKE 의 % 는 "아무 글자 0개 이상". 검색어는 %s 자리에 넣고 % 는 파이썬에서 붙임
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 이름에 검색어가 들어간 사용자 (가운데 일치: %검색어%)
def users_by_name(keyword="사용자0"):
    sql = """
        SELECT u.user_id, u.user_name, u.gender, u.email
        FROM body.users AS u
        WHERE u.user_name LIKE %s
        ORDER BY u.user_name
    """
    return query(sql, ("%" + keyword + "%",))


# 목적: 이메일 도메인이 같은 사용자 (뒤 일치: %@도메인)
def users_by_email_domain(domain="example.com"):
    sql = """
        SELECT u.user_id, u.user_name, u.email
        FROM body.users AS u
        WHERE u.email LIKE %s
        ORDER BY u.email
    """
    return query(sql, ("%@" + domain,))


# 목적: 이메일이 특정 글자로 시작하는 사용자 (앞 일치: 글자%)
def users_by_email_prefix(prefix="user0"):
    sql = """
        SELECT u.user_id, u.user_name, u.email
        FROM body.users AS u
        WHERE u.email LIKE %s
        ORDER BY u.user_id
    """
    return query(sql, (prefix + "%",))


if __name__ == "__main__":
    show("이름에 '사용자0' 이 들어간 사용자", users_by_name("사용자0"))
    show("이메일 도메인 = example.com", users_by_email_domain("example.com"))
    show("이메일이 'user03' 으로 시작", users_by_email_prefix("user03"))
