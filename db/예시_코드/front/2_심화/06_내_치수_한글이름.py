# 목적: "내 치수" 화면 — email 로 가장 최근 신체 정보를 찾고, 그 치수를 영어 코드 대신 한글 이름·부위와 함께 보여 주기
# 누가 쓰나: 프론트
# 난이도: 심화 — 2개 표 JOIN 두 번 (users ↔ profiles 로 최근 profile_id, measures ↔ measure_definitions 로 한글 이름)
# 출력: user01(profile 18) 치수 23행(korean_name·value_cm·body_part·measure_method), nobody 는 '신체 정보 없음'
# 실행: .venv/bin/python db/예시_코드/front/2_심화/06_내_치수_한글이름.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: email → 그 사람의 가장 최근 profile_id (없으면 None)
def latest_profile_id(email):
    sql = """
        SELECT p.profile_id
        FROM body.users AS u
        JOIN body.profiles AS p ON p.user_id = u.user_id
        WHERE u.email = %s
        ORDER BY p.created_at DESC, p.profile_id DESC
        LIMIT 1
    """
    rows = query(sql, (email,))
    if len(rows) == 0:
        return None
    return rows[0]["profile_id"]


# 목적: profile_id 의 치수 + 한글 이름 + 실측/추정 표시
def my_measures(profile_id):
    sql = """
        SELECT d.korean_name, m.value_cm, d.body_part, m.measure_method, m.measure_code
        FROM body.measures AS m
        JOIN ref.measure_definitions AS d ON d.measure_code = m.measure_code
        WHERE m.profile_id = %s
        ORDER BY FIELD(d.body_part, 'full', 'neck', 'torso', 'arm', 'leg'), d.korean_name
    """
    return query(sql, (profile_id,))


if __name__ == "__main__":
    for email in ["user01@example.com", "nobody@example.com"]:
        profile_id = latest_profile_id(email)
        if profile_id is None:
            print()
            print("■ " + email + " → 신체 정보 없음 (가입 안 했거나 아직 입력 전)")
            continue
        show("내 치수 (email = " + email + ", profile_id = " + str(profile_id) + ")", my_measures(profile_id))
