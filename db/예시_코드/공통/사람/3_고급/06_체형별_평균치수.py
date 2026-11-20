# 목적: 성별 × 체형별 평균 치수, 사람마다 부위별 치수 개수 표, 저장된 체형이 BMI 와 맞는지 SQL 로 검사
# 누가 쓰나: 공통 (3D 체형별 대표 몸, AI 데이터 살펴보기, 프론트 통계 화면)
# 난이도: 고급 — 4개 표 LEFT JOIN + 조건부 집계 피벗 AVG/SUM(CASE ...) + 파생 테이블 안의 BMI CASE
# 출력: 표 3개 — 성별×체형 평균 가슴·허리·엉덩이·어깨(8행), 사람별 부위 치수 개수(10행), 체형↔BMI 검사(22행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/3_고급/06_체형별_평균치수.py
# 체형 기준: 대한비만학회 BMI 단계 (_body_type.py, db/sql/24_body_profiles_body_type.sql)
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show
from _body_type import body_type_of, body_type_name            # 파이썬 계산과 SQL 계산 비교용


# 목적: 성별 × 체형마다 사람 수와 주요 치수 평균 (치수는 실측 measured 만). 세로 치수 행 → 치수별 열
def avg_by_body_type():
    sql = """
        SELECT p.gender, p.body_type,
               COUNT(DISTINCT p.profile_id) AS people_tally,
               ROUND(AVG(CASE WHEN m.measure_code = 'chest_girth' THEN m.value_cm END), 1) AS chest_girth,
               ROUND(AVG(CASE WHEN m.measure_code = 'waist_girth' THEN m.value_cm END), 1) AS waist_girth,
               ROUND(AVG(CASE WHEN m.measure_code = 'hip_girth' THEN m.value_cm END), 1) AS hip_girth,
               ROUND(AVG(CASE WHEN m.measure_code = 'shoulder_width' THEN m.value_cm END), 1) AS shoulder_width
        FROM body.profiles AS p
        JOIN body.measures AS m ON m.profile_id = p.profile_id
        WHERE m.measure_method = 'measured'
        GROUP BY p.gender, p.body_type
        ORDER BY p.gender, p.body_type
    """
    rows = query(sql)
    for row in rows:
        row["체형"] = body_type_name(row["body_type"])
    return rows


# 목적: 사람마다 부위(full·torso·arm·leg·neck)별 치수 개수 → 1명 = 1행 (치수가 있는 사람만)
def part_tally_by_person():
    sql = """
        SELECT p.profile_id, u.user_name, p.source_name, p.gender,
               SUM(CASE WHEN d.body_part = 'full'  THEN 1 ELSE 0 END) AS full_tally,
               SUM(CASE WHEN d.body_part = 'torso' THEN 1 ELSE 0 END) AS torso_tally,
               SUM(CASE WHEN d.body_part = 'arm'   THEN 1 ELSE 0 END) AS arm_tally,
               SUM(CASE WHEN d.body_part = 'leg'   THEN 1 ELSE 0 END) AS leg_tally,
               SUM(CASE WHEN d.body_part = 'neck'  THEN 1 ELSE 0 END) AS neck_tally,
               COUNT(m.measure_code) AS measure_tally
        FROM body.profiles AS p
        LEFT JOIN body.users AS u ON u.user_id = p.user_id
        LEFT JOIN body.measures AS m ON m.profile_id = p.profile_id
        LEFT JOIN ref.measure_definitions AS d ON d.measure_code = m.measure_code
        GROUP BY p.profile_id, u.user_name, p.source_name, p.gender
        HAVING COUNT(m.measure_code) > 0
        ORDER BY p.profile_id
    """
    return query(sql)


# 목적: 저장된 body_type 이 키·체중 BMI 단계와 같은지 SQL 로 검사 (파생 테이블 t 안에서 BMI·단계 계산)
# 같은 검사를 파이썬(_body_type.body_type_of)으로도 해서 python_type 열에 같이 보여 줌
def body_type_check():
    sql = """
        SELECT t.profile_id, t.source_name, t.bmi, t.body_type, t.bmi_type,
               CASE WHEN t.body_type = t.bmi_type THEN 'same' ELSE 'diff' END AS check_result,
               t.height_cm, t.weight_kg
        FROM (
            SELECT p.profile_id, p.source_name, p.body_type, p.height_cm, p.weight_kg,
                   ROUND(p.weight_kg / POW(p.height_cm / 100, 2), 1) AS bmi,
                   CASE
                       WHEN p.weight_kg / POW(p.height_cm / 100, 2) < 18.5 THEN 'underweight'
                       WHEN p.weight_kg / POW(p.height_cm / 100, 2) < 23   THEN 'normal'
                       WHEN p.weight_kg / POW(p.height_cm / 100, 2) < 25   THEN 'pre_obese'
                       WHEN p.weight_kg / POW(p.height_cm / 100, 2) < 30   THEN 'obese_1'
                       WHEN p.weight_kg / POW(p.height_cm / 100, 2) < 35   THEN 'obese_2'
                       ELSE 'obese_3'
                   END AS bmi_type
            FROM body.profiles AS p
            WHERE p.height_cm IS NOT NULL
              AND p.weight_kg IS NOT NULL
        ) AS t
        ORDER BY t.profile_id
    """
    rows = query(sql)
    for row in rows:
        row["python_type"] = body_type_of(row["height_cm"], row["weight_kg"])
        del row["height_cm"]
        del row["weight_kg"]
    return rows


# 목적: 검사 결과 요약 한 줄 (같음 / 다름 개수)
def print_check_summary(rows):
    same = 0
    diff = 0
    for row in rows:
        if row["check_result"] == "same" and row["python_type"] == row["bmi_type"]:
            same += 1
        else:
            diff += 1
    print("  → 저장값 = SQL 계산 = 파이썬 계산: " + str(same) + "명, 다름: " + str(diff) + "명")


if __name__ == "__main__":
    show("성별 × 체형별 평균 치수 (실측, cm)", avg_by_body_type())
    show("사람마다 부위별 치수 개수 (치수 있는 사람만)", part_tally_by_person())
    rows = body_type_check()
    show("저장된 체형 ↔ BMI 단계 검사", rows)
    print_check_summary(rows)
