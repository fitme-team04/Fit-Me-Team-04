# 목적: 성별 안에서 키 순위·사분위(4등분)·백분위, 그리고 성별 키 중앙값 (내 키가 같은 성별에서 몇 % 쯤인지)
# 누가 쓰나: 공통 (프론트 "상위 몇 %" 안내, 3D 사분위별 대표 몸, AI 분포 확인)
# 난이도: 고급 — 창 함수 RANK·NTILE·ROW_NUMBER·COUNT(*) OVER (PARTITION BY gender) + 파생 테이블로 백분위·중앙값 계산
# 출력: 표 2개 — 성별 키 순위·사분위·백분위(22행), 성별 키 중앙값·사람 수(2행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/3_고급/03_성별_키_순위.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 사람마다 성별 안 키 순위(큰 순 RANK), 사분위(NTILE 4, 1 = 가장 작은 25%), 백분위(작은 순 위치 0~100)
def height_ranks():
    sql = """
        SELECT t.profile_id, t.gender, t.source_name, t.height_cm,
               t.height_rank, t.quartile,
               ROUND(100 * (t.row_no - 1) / (t.gender_tally - 1), 0) AS percentile
        FROM (
            SELECT p.profile_id, p.gender, p.source_name, p.height_cm,
                   RANK()       OVER (PARTITION BY p.gender ORDER BY p.height_cm DESC) AS height_rank,
                   NTILE(4)     OVER (PARTITION BY p.gender ORDER BY p.height_cm) AS quartile,
                   ROW_NUMBER() OVER (PARTITION BY p.gender ORDER BY p.height_cm, p.profile_id) AS row_no,
                   COUNT(*)     OVER (PARTITION BY p.gender) AS gender_tally
            FROM body.profiles AS p
            WHERE p.height_cm IS NOT NULL
        ) AS t
        ORDER BY t.gender, t.height_rank
    """
    return query(sql)


# 목적: 성별 키 중앙값 — 작은 순 번호(ROW_NUMBER)가 가운데인 1명(홀수) 또는 2명(짝수)의 평균
def median_height_by_gender():
    sql = """
        SELECT t.gender, ROUND(AVG(t.height_cm), 1) AS median_height_cm, MAX(t.gender_tally) AS people_tally
        FROM (
            SELECT p.gender, p.height_cm,
                   ROW_NUMBER() OVER (PARTITION BY p.gender ORDER BY p.height_cm) AS row_no,
                   COUNT(*)     OVER (PARTITION BY p.gender) AS gender_tally
            FROM body.profiles AS p
            WHERE p.height_cm IS NOT NULL
        ) AS t
        WHERE t.row_no IN (FLOOR((t.gender_tally + 1) / 2), CEIL((t.gender_tally + 1) / 2))
        GROUP BY t.gender
        ORDER BY t.gender
    """
    return query(sql)


if __name__ == "__main__":
    show("성별 키 순위·사분위·백분위", height_ranks())
    show("성별 키 중앙값 (ROW_NUMBER 가운데 행)", median_height_by_gender())
