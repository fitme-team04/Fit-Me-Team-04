# 목적: 생년월일 범위로 사용자 찾기 (예: 1990년대생), 가입자의 출생 연도 목록
# 누가 쓰나: 공통 (프론트 통계 화면, 나이대별 회원 고르기)
# 난이도: 기본 — 표 1개(body.users) SELECT + WHERE BETWEEN·DISTINCT·YEAR()
# 출력: 표 3개 — 1990년대생 사용자(이름·성별·생일, 3행), 2000년 이후 출생(1행), 가입자 출생 연도 DISTINCT(5행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/1_기본/08_출생연도_범위_사용자.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 출생 연도 from_year ~ to_year (양 끝 포함) 사용자. 날짜 열은 'YYYY-01-01' ~ 'YYYY-12-31' 로 비교
def users_born_between(from_year=1990, to_year=1999):
    sql = """
        SELECT u.user_id, u.user_name, u.gender, u.birth_date
        FROM body.users AS u
        WHERE u.birth_date BETWEEN %s AND %s
        ORDER BY u.birth_date
    """
    start = str(from_year) + "-01-01"
    end = str(to_year) + "-12-31"
    return query(sql, (start, end))


# 목적: 가입자의 출생 연도 목록 (같은 해는 한 번만, DISTINCT)
def birth_years():
    sql = """
        SELECT DISTINCT YEAR(u.birth_date) AS birth_year
        FROM body.users AS u
        WHERE u.birth_date IS NOT NULL
        ORDER BY birth_year
    """
    return query(sql)


if __name__ == "__main__":
    show("1990년대생 사용자 (1990-01-01 ~ 1999-12-31)", users_born_between(1990, 1999))
    show("2000년 이후 출생 사용자", users_born_between(2000, 2099))
    show("가입자의 출생 연도 (DISTINCT)", birth_years())
