# 목적: BMI 를 일정 폭(기본 5)으로 나눈 구간별 사람 수 — 성별 열 피벗 + 누적 사람 수·누적 비율 (BMI 분포 그래프 자료)
# 누가 쓰나: 공통 (AI BMI 분포 확인, 프론트 통계 그래프)
# 난이도: 고급 — CTE(WITH) 안 BMI 계산식 + 조건부 집계 피벗 + 창 함수 SUM(...) OVER (ORDER BY ...) 누적 합
# 출력: 표 2개 — BMI 5단위 구간 남/여 수·누적 수·누적%·막대(5행), BMI 2단위 구간(11행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/3_고급/02_BMI_구간_분포.py
# 체형 단계(저체중·정상 …)별 사람 수는 2_심화/05_사용자_신체정보_목록.py, 여기는 숫자 구간 분포
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: BMI 구간(width 단위로 내림)마다 남·여·전체 사람 수와 누적 사람 수·누적 %
def bmi_distribution(width=5):
    sql = """
        WITH bmi AS (
            SELECT p.profile_id, p.gender,
                   p.weight_kg / POW(p.height_cm / 100, 2) AS bmi
            FROM body.profiles AS p
            WHERE p.height_cm IS NOT NULL
              AND p.weight_kg IS NOT NULL
        ),
        bands AS (
            SELECT FLOOR(b.bmi / %s) * %s AS bmi_from,
                   SUM(CASE WHEN b.gender = 'male'   THEN 1 ELSE 0 END) AS male_tally,
                   SUM(CASE WHEN b.gender = 'female' THEN 1 ELSE 0 END) AS female_tally,
                   COUNT(*) AS people_tally
            FROM bmi AS b
            GROUP BY FLOOR(b.bmi / %s) * %s
        )
        SELECT t.bmi_from, t.male_tally, t.female_tally, t.people_tally,
               SUM(t.people_tally) OVER (ORDER BY t.bmi_from) AS cumulative_tally,
               ROUND(100 * SUM(t.people_tally) OVER (ORDER BY t.bmi_from)
                     / SUM(t.people_tally) OVER (), 1) AS cumulative_pct
        FROM bands AS t
        ORDER BY t.bmi_from
    """
    rows = query(sql, (width, width, width, width))
    for row in rows:
        start = int(row["bmi_from"])
        row["구간"] = str(start) + " ~ " + str(start + width) + " 미만"
        row["막대"] = "#" * int(row["people_tally"])
    return rows


if __name__ == "__main__":
    show("BMI 5 단위 구간 분포 (성별 피벗 + 누적)", bmi_distribution(5))
    show("BMI 2 단위 구간 분포", bmi_distribution(2))
