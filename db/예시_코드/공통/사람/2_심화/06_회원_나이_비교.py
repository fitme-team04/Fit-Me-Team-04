# 목적: 회원이 신체 정보에 적은 나이(profiles.age)와 생년월일로 계산한 지금 나이가 맞는지 비교
# 누가 쓰나: 공통 (프론트 입력값 점검, AI 나이 열 정리)
# 난이도: 심화 — 2개 표 JOIN(사용자 + 신체 정보) + 날짜 계산식(TIMESTAMPDIFF) + 차이 열
# 출력: 표 2개 — 회원 입력 나이↔생년월일 계산 나이·차이·판정(5행), 남성 회원 나이 많은 순(3행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/2_심화/06_회원_나이_비교.py
# 신체 정보의 age 는 입력한 그때 나이라 시간이 지나면 1~2살 차이가 날 수 있음 (차이 0~1 은 정상)
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 회원마다 입력 나이·지금 나이·입력 당시 나이(생년월일 → 신체 정보 입력일)·차이
def member_age_check():
    sql = """
        SELECT u.user_id, u.user_name, u.birth_date,
               p.profile_id, p.age AS profile_age,
               TIMESTAMPDIFF(YEAR, u.birth_date, p.created_at) AS age_at_input,
               TIMESTAMPDIFF(YEAR, u.birth_date, CURDATE()) AS age_now,
               p.age - TIMESTAMPDIFF(YEAR, u.birth_date, p.created_at) AS age_diff
        FROM body.users AS u
        JOIN body.profiles AS p ON p.user_id = u.user_id
        ORDER BY u.user_id, p.profile_id
    """
    rows = query(sql)
    for row in rows:
        diff = row["age_diff"]
        if diff is None:
            row["판정"] = "나이 없음"
        elif diff >= -1 and diff <= 1:
            row["판정"] = "정상"
        else:
            row["판정"] = "확인 필요"
    return rows


# 목적: 성별 한 가지 회원만 (JOIN 뒤 WHERE 로 거르기)
def member_age_check_by_gender(gender="male"):
    sql = """
        SELECT u.user_id, u.user_name, u.gender, p.age AS profile_age,
               TIMESTAMPDIFF(YEAR, u.birth_date, CURDATE()) AS age_now
        FROM body.users AS u
        JOIN body.profiles AS p ON p.user_id = u.user_id
        WHERE u.gender = %s
        ORDER BY age_now DESC
    """
    return query(sql, (gender,))


if __name__ == "__main__":
    show("회원 나이 비교 (입력 나이 ↔ 생년월일 계산)", member_age_check())
    show("남성 회원 나이 (나이 많은 순)", member_age_check_by_gender("male"))
