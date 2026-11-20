# 목적: 나이대(20대·30대·40대)마다 키·체중으로 계산한 BMI 단계 사람 수 피벗과 비만율(BMI ≥ 25 비율), 성별 나눠 보기
# 누가 쓰나: 공통 (AI 나이 × 체형 치우침 확인, 프론트 통계 화면)
# 난이도: 고급 — CTE 안 BMI CASE(대한비만학회 단계) + 나이대 계산식 + 조건부 집계 피벗 + 비율 계산식
# 출력: 표 2개 — 나이대별 BMI 단계 수·평균 BMI·비만율%(3행), 나이대×성별 사람 수·비만율%(3행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/3_고급/05_나이대별_비만율.py
# 체형 기준: 대한비만학회(KSSO) 비만 진료지침 2022 표 1 — BMI ≥ 25 비만 (_body_type.py 와 같은 경계)
# 나이가 NULL 인 사람(BodyM)은 나이대를 알 수 없어 뺌. 나이대별 사람 수만은 2_심화/02_나이대별_사람수.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show

# 단계 계산 CTE (저장된 body_type 대신 키·체중으로 바로 계산). 아래 두 함수가 같이 씀
STAGE_CTE = """
    WITH staged AS (
        SELECT p.profile_id, p.gender, FLOOR(p.age / 10) * 10 AS age_band,
               p.weight_kg / POW(p.height_cm / 100, 2) AS bmi,
               CASE
                   WHEN p.weight_kg / POW(p.height_cm / 100, 2) < 18.5 THEN 'underweight'
                   WHEN p.weight_kg / POW(p.height_cm / 100, 2) < 23   THEN 'normal'
                   WHEN p.weight_kg / POW(p.height_cm / 100, 2) < 25   THEN 'pre_obese'
                   ELSE 'obese'
               END AS stage
        FROM body.profiles AS p
        WHERE p.age IS NOT NULL
          AND p.height_cm IS NOT NULL
          AND p.weight_kg IS NOT NULL
    )
"""


# 목적: 나이대마다 단계별 사람 수 피벗 + 평균 BMI + 비만율 %
def obesity_by_age_band():
    sql = STAGE_CTE + """
        SELECT s.age_band,
               COUNT(*) AS people_tally,
               SUM(CASE WHEN s.stage = 'underweight' THEN 1 ELSE 0 END) AS underweight,
               SUM(CASE WHEN s.stage = 'normal'      THEN 1 ELSE 0 END) AS normal,
               SUM(CASE WHEN s.stage = 'pre_obese'   THEN 1 ELSE 0 END) AS pre_obese,
               SUM(CASE WHEN s.stage = 'obese'       THEN 1 ELSE 0 END) AS obese,
               ROUND(AVG(s.bmi), 1) AS avg_bmi,
               ROUND(100 * SUM(CASE WHEN s.stage = 'obese' THEN 1 ELSE 0 END) / COUNT(*), 1) AS obese_pct
        FROM staged AS s
        GROUP BY s.age_band
        ORDER BY s.age_band
    """
    return query(sql)


# 목적: 나이대 × 성별 비만율 (남·여 비만율을 열로 나란히)
def obesity_by_age_band_gender():
    sql = STAGE_CTE + """
        SELECT s.age_band,
               SUM(CASE WHEN s.gender = 'male' THEN 1 ELSE 0 END) AS male_tally,
               ROUND(100 * SUM(CASE WHEN s.gender = 'male' AND s.stage = 'obese' THEN 1 ELSE 0 END)
                     / NULLIF(SUM(CASE WHEN s.gender = 'male' THEN 1 ELSE 0 END), 0), 1) AS male_obese_pct,
               SUM(CASE WHEN s.gender = 'female' THEN 1 ELSE 0 END) AS female_tally,
               ROUND(100 * SUM(CASE WHEN s.gender = 'female' AND s.stage = 'obese' THEN 1 ELSE 0 END)
                     / NULLIF(SUM(CASE WHEN s.gender = 'female' THEN 1 ELSE 0 END), 0), 1) AS female_obese_pct
        FROM staged AS s
        GROUP BY s.age_band
        ORDER BY s.age_band
    """
    return query(sql)


if __name__ == "__main__":
    show("나이대별 BMI 단계 피벗 + 비만율", obesity_by_age_band())
    show("나이대 × 성별 비만율 (NULL = 그 나이대에 그 성별 없음)", obesity_by_age_band_gender())
