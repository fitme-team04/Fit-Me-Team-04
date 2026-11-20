# 목적: 성별 하나의 사람 수·출처 개수·회원 수 세기 (GROUP BY 없이 성별마다 한 번씩 COUNT)
# 누가 쓰나: 공통 (AI 데이터 균형 확인, 프론트 통계 화면)
# 난이도: 기본 — 표 1개(body.profiles) SELECT + WHERE + COUNT(*)·COUNT(열)·COUNT(DISTINCT 열)
# 출력: 표 1개 — 성별 사람 수(전체·회원·출처 종류·나이 있음), male·female 2행(각 11명)
# 실행: .venv/bin/python db/예시_코드/공통/사람/1_기본/09_성별_사람수_세기.py
# 성별을 한 번에 묶어 세는 GROUP BY 는 2_심화 에서 다룸
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 성별 하나의 사람 수, 회원 수(user_id 있는 행), 출처 종류 수, 나이 있는 사람 수
def gender_tally(gender="female"):
    sql = """
        SELECT %s AS gender,
               COUNT(*) AS people_tally,
               COUNT(p.user_id) AS member_tally,
               COUNT(DISTINCT p.source_name) AS source_tally,
               COUNT(p.age) AS with_age_tally
        FROM body.profiles AS p
        WHERE p.gender = %s
    """
    rows = query(sql, (gender, gender))
    return rows[0]


if __name__ == "__main__":
    rows = []
    for gender in ["male", "female"]:
        rows.append(gender_tally(gender))
    show("성별 사람 수 (성별마다 COUNT 한 번)", rows)
