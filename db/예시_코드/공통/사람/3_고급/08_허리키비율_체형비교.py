# 목적: 사람마다 허리둘레 ÷ 키 비율(WHtR)과 한국인 복부비만 허리둘레 기준 해당 여부, 체형(body_type)별 평균·해당 비율 비교
# 누가 쓰나: 공통 (BMI 체형과 복부비만이 어긋나는 사람 찾기, AI 체형 특징 열, 3D 몸통 둘레 확인)
# 난이도: 고급 — CTE 2개(피벗 + 계산) + 4개 표 JOIN(치수·항목 정의·신체 정보·사용자) + 비율 계산식 + 조건부 집계
# 출력: 표 2개 — 사람별 키·허리·WHtR·초과 여부·복부비만(10행), 체형별 평균 WHtR·초과%·복부비만%(6행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/3_고급/08_허리키비율_체형비교.py
# 기준 1: 대한비만학회(KSSO) 비만 진료지침 2022 — 복부비만 허리둘레 남성 ≥ 90cm, 여성 ≥ 85cm
#   https://general.kosso.or.kr/html/user/core/view/reaction/main/kosso/inc/data/guideline2022_vol8.pdf
# 기준 2: 허리-키 비율(WHtR) 0.5 이상을 위험 신호로 보는 경계값 (Ashwell & Hsieh 2005, "keep your waist to less than half your height")
# 키는 body.profiles.height_cm 를 씀 (치수 height 가 없는 사람도 계산되게). 허리-엉덩이 비율은 07_허리엉덩이비_순위.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show
from _body_type import BODY_TYPES, body_type_name               # 체형 순서·한글 이름

WAIST_MALE_CM = 90      # KSSO 남성 복부비만
WAIST_FEMALE_CM = 85    # KSSO 여성 복부비만
WHTR_CUT = 0.5          # 허리-키 비율 경계

# 허리둘레(waist_girth, 한글 이름은 항목 정의에서) + 키 → 비율·판정. 아래 두 함수가 같이 씀
WHTR_CTE = """
    WITH waist AS (
        SELECT m.profile_id, d.korean_name,
               MAX(CASE WHEN m.measure_code = 'waist_girth' THEN m.value_cm END) AS waist_cm
        FROM body.measures AS m
        JOIN ref.measure_definitions AS d ON d.measure_code = m.measure_code
        WHERE d.measure_code = 'waist_girth'
        GROUP BY m.profile_id, d.korean_name
    ),
    judged AS (
        SELECT p.profile_id, u.user_name, p.source_name, p.gender, p.body_type,
               p.height_cm, w.waist_cm,
               ROUND(w.waist_cm / p.height_cm, 3) AS whtr,
               CASE WHEN w.waist_cm / p.height_cm >= %s THEN 1 ELSE 0 END AS whtr_over,
               CASE
                   WHEN p.gender = 'male'   AND w.waist_cm >= %s THEN 1
                   WHEN p.gender = 'female' AND w.waist_cm >= %s THEN 1
                   ELSE 0
               END AS abdominal_obese
        FROM waist AS w
        JOIN body.profiles AS p ON p.profile_id = w.profile_id
        LEFT JOIN body.users AS u ON u.user_id = p.user_id
        WHERE p.height_cm IS NOT NULL
    )
"""
CTE_PARAMS = (WHTR_CUT, WAIST_MALE_CM, WAIST_FEMALE_CM)


# 목적: 사람마다 허리-키 비율·복부비만 해당 여부 (비율 큰 순)
def whtr_people():
    sql = WHTR_CTE + """
        SELECT j.profile_id, j.user_name, j.source_name, j.gender, j.body_type,
               j.height_cm, j.waist_cm, j.whtr, j.whtr_over, j.abdominal_obese
        FROM judged AS j
        ORDER BY j.whtr DESC
    """
    rows = query(sql, CTE_PARAMS)
    for row in rows:
        row["체형"] = body_type_name(row["body_type"])
    return rows


# 목적: 체형마다 사람 수·평균 허리-키 비율·비율 0.5 이상 %·복부비만 % (BMI 체형과 허리 기준 비교)
def whtr_by_body_type():
    sql = WHTR_CTE + """
        SELECT j.body_type,
               COUNT(*) AS people_tally,
               ROUND(AVG(j.whtr), 3) AS avg_whtr,
               ROUND(100 * SUM(j.whtr_over) / COUNT(*), 1) AS whtr_over_pct,
               ROUND(100 * SUM(j.abdominal_obese) / COUNT(*), 1) AS abdominal_obese_pct
        FROM judged AS j
        GROUP BY j.body_type
    """
    found = {}
    for row in query(sql, CTE_PARAMS):
        found[row["body_type"]] = row
    result = []
    for body_type in BODY_TYPES:                 # BMI 작은 단계부터
        if body_type in found:
            row = found[body_type]
            row["체형"] = body_type_name(body_type)
            result.append(row)
    return result


if __name__ == "__main__":
    show("사람별 허리-키 비율(WHtR)·복부비만(KSSO 허리둘레) 여부", whtr_people())
    show("체형별 허리-키 비율·복부비만 비율", whtr_by_body_type())
