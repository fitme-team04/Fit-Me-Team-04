# 목적: 사람마다 허리-엉덩이 둘레 비율(WHR = 허리 ÷ 엉덩이)과 성별 안 순위, 복부비만 기준 넘는지, 성별 상위 N명
# 누가 쓰나: 공통 (3D 몸통 실루엣 유형 고르기, AI 체형 특징 열, 프론트 통계)
# 난이도: 고급 — CTE 안 세로 → 가로 피벗 MAX(CASE ...) + 3개 표 JOIN + 비율 계산식 + 창 함수 RANK·ROW_NUMBER OVER (PARTITION BY)
# 출력: 표 2개 — 허리·엉덩이 둘레·WHR·등급·순위(10행), 성별 WHR 상위 2명(4행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/3_고급/07_허리엉덩이비_순위.py
# 기준: WHO "Waist circumference and waist-hip ratio: report of a WHO expert consultation" (2008)
#   — WHR 남성 ≥ 0.90, 여성 ≥ 0.85 이면 복부비만(대사 합병증 위험 큼). https://www.who.int/publications/i/item/9789241501491
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show

WHR_MALE = 0.90      # WHO 2008 남성 기준
WHR_FEMALE = 0.85    # WHO 2008 여성 기준

# 허리·엉덩이 둘레를 1명 = 1행으로 펼친 CTE (둘 다 있는 사람만 남김). 아래 두 함수가 같이 씀
WHR_CTE = """
    WITH wh AS (
        SELECT m.profile_id,
               MAX(CASE WHEN m.measure_code = 'waist_girth' THEN m.value_cm END) AS waist_cm,
               MAX(CASE WHEN m.measure_code = 'hip_girth'   THEN m.value_cm END) AS hip_cm
        FROM body.measures AS m
        WHERE m.measure_code IN ('waist_girth', 'hip_girth')
        GROUP BY m.profile_id
        HAVING COUNT(*) = 2
    ),
    ratio AS (
        SELECT p.profile_id, u.user_name, p.source_name, p.gender, wh.waist_cm, wh.hip_cm,
               ROUND(wh.waist_cm / wh.hip_cm, 3) AS whr,
               CASE
                   WHEN p.gender = 'male'   AND wh.waist_cm / wh.hip_cm >= %s THEN 'high'
                   WHEN p.gender = 'female' AND wh.waist_cm / wh.hip_cm >= %s THEN 'high'
                   ELSE 'normal'
               END AS whr_level
        FROM wh
        JOIN body.profiles AS p ON p.profile_id = wh.profile_id
        LEFT JOIN body.users AS u ON u.user_id = p.user_id
    )
"""


# 목적: 허리-엉덩이 비율이 있는 사람 전부 + 성별 안 순위(비율 큰 순 RANK)
def whr_ranking():
    sql = WHR_CTE + """
        SELECT r.*, RANK() OVER (PARTITION BY r.gender ORDER BY r.whr DESC) AS whr_rank
        FROM ratio AS r
        ORDER BY r.gender, whr_rank
    """
    return query(sql, (WHR_MALE, WHR_FEMALE))


# 목적: 성별마다 비율이 가장 큰 top_n 명 (ROW_NUMBER 로 번호 매긴 뒤 바깥에서 거름)
def whr_top_by_gender(top_n=2):
    sql = WHR_CTE + """
        SELECT t.gender, t.row_no, t.profile_id, t.source_name, t.whr, t.whr_level
        FROM (
            SELECT r.*, ROW_NUMBER() OVER (PARTITION BY r.gender ORDER BY r.whr DESC, r.profile_id) AS row_no
            FROM ratio AS r
        ) AS t
        WHERE t.row_no <= %s
        ORDER BY t.gender, t.row_no
    """
    return query(sql, (WHR_MALE, WHR_FEMALE, top_n))


if __name__ == "__main__":
    show("허리-엉덩이 비율(WHR) 순위 (high = WHO 복부비만 기준 이상)", whr_ranking())
    show("성별 WHR 상위 2명", whr_top_by_gender(2))
