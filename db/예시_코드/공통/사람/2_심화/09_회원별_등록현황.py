# 목적: 회원마다 신체 정보를 몇 번 입력했고 치수는 몇 개, 실측·추정이 각각 몇 개인지 (회원 등록 진행 상황)
# 누가 쓰나: 공통 (프론트 회원 관리, AI 추정값 비율 확인)
# 난이도: 심화 — 3개 표 LEFT JOIN(사용자 → 신체 정보 → 치수) + GROUP BY + COUNT(DISTINCT)·SUM(CASE)·MAX
# 출력: 표 2개 — 회원별 프로필·치수·실측/추정 수·최근 입력일(5행), 치수 25개 미만 회원 HAVING(5행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/2_심화/09_회원별_등록현황.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 회원 1명 = 1행 (신체 정보·치수가 없는 회원도 0 으로 나오도록 LEFT JOIN)
def member_status():
    sql = """
        SELECT u.user_id, u.user_name, u.gender,
               COUNT(DISTINCT p.profile_id) AS profile_tally,
               COUNT(m.measure_code) AS measure_tally,
               SUM(CASE WHEN m.measure_method = 'measured' THEN 1 ELSE 0 END) AS measured_tally,
               SUM(CASE WHEN m.measure_method = 'estimated' THEN 1 ELSE 0 END) AS estimated_tally,
               MAX(p.created_at) AS last_input_at
        FROM body.users AS u
        LEFT JOIN body.profiles AS p ON p.user_id = u.user_id
        LEFT JOIN body.measures AS m ON m.profile_id = p.profile_id
        GROUP BY u.user_id, u.user_name, u.gender
        ORDER BY u.user_id
    """
    return query(sql)


# 목적: 치수가 min_tally 개 미만인 회원만 (입력이 덜 된 회원, HAVING)
def members_with_few_measures(min_tally=20):
    sql = """
        SELECT u.user_id, u.user_name, COUNT(m.measure_code) AS measure_tally
        FROM body.users AS u
        LEFT JOIN body.profiles AS p ON p.user_id = u.user_id
        LEFT JOIN body.measures AS m ON m.profile_id = p.profile_id
        GROUP BY u.user_id, u.user_name
        HAVING COUNT(m.measure_code) < %s
        ORDER BY measure_tally, u.user_id
    """
    return query(sql, (min_tally,))


if __name__ == "__main__":
    show("회원별 등록 현황", member_status())
    show("치수가 25개 미만인 회원 (HAVING)", members_with_few_measures(25))
