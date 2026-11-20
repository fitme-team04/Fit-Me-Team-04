# 목적: 3D 몸 비례 계산 — 팔길이/키, 다리안쪽길이/키, 허리/엉덩이 둘레, 어깨너비/가슴너비, 가슴 두께/너비(단면 납작함)
# 누가 쓰나: 3D
# 난이도: 고급 — CTE(WITH) 안 조건부 집계 피벗 + 비율 계산식(NULLIF 로 0 나누기 막기) + 바깥 GROUP BY 성별 평균
# 출력: 신체 비율 표 3개 — 전체(10행)·여성만(5행)·성별 평균(2행); arm/leg_to_height·waist_to_hip·shoulder_to_chest 등
# 실행: .venv/bin/python db/예시_코드/3d/3_고급/03_신체비율_계산.py
# 비율은 단위가 없는 값(cm/cm). 키 비율은 3D 뼈 길이, 둘레·너비 비율은 몸통 모양(체형 블렌드)에 씀
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show

# 두 함수가 같이 쓰는 CTE: 사람마다 비율에 필요한 치수 7개를 한 행으로 + 비율
RATIO_CTE = """
    WITH wide AS (
        SELECT m.profile_id,
               MAX(CASE WHEN m.measure_code = 'height'         THEN m.value_cm END) AS height,
               MAX(CASE WHEN m.measure_code = 'arm_length'     THEN m.value_cm END) AS arm_length,
               MAX(CASE WHEN m.measure_code = 'inseam'         THEN m.value_cm END) AS inseam,
               MAX(CASE WHEN m.measure_code = 'waist_girth'    THEN m.value_cm END) AS waist_girth,
               MAX(CASE WHEN m.measure_code = 'hip_girth'      THEN m.value_cm END) AS hip_girth,
               MAX(CASE WHEN m.measure_code = 'shoulder_width' THEN m.value_cm END) AS shoulder_width,
               MAX(CASE WHEN m.measure_code = 'chest_breadth'  THEN m.value_cm END) AS chest_breadth,
               MAX(CASE WHEN m.measure_code = 'chest_depth'    THEN m.value_cm END) AS chest_depth
        FROM body.measures AS m
        GROUP BY m.profile_id
    ),
    ratios AS (
        SELECT p.profile_id, p.gender, p.body_type,
               ROUND(w.arm_length     / NULLIF(COALESCE(w.height, p.height_cm), 0), 3) AS arm_to_height,
               ROUND(w.inseam         / NULLIF(COALESCE(w.height, p.height_cm), 0), 3) AS leg_to_height,
               ROUND(w.waist_girth    / NULLIF(w.hip_girth, 0), 3)                     AS waist_to_hip,
               ROUND(w.shoulder_width / NULLIF(w.chest_breadth, 0), 3)                 AS shoulder_to_chest,
               ROUND(w.chest_depth    / NULLIF(w.chest_breadth, 0), 3)                 AS chest_depth_to_breadth
        FROM wide AS w
        JOIN body.profiles AS p ON p.profile_id = w.profile_id
    )
"""


# 목적: 사람마다 비율 (gender 가 None 이면 전부). 허리/엉덩이 비율이 없는 사람은 뺌
def body_ratios(gender=None):
    sql = RATIO_CTE + """
        SELECT r.*
        FROM ratios AS r
        WHERE r.waist_to_hip IS NOT NULL
          AND (%s IS NULL OR r.gender = %s)
        ORDER BY r.gender, r.profile_id
    """
    return query(sql, (gender, gender))


# 목적: 성별 평균 비율 (AVG 는 NULL 을 빼고 계산 → 사람 수는 비율마다 다를 수 있음)
def ratio_means_by_gender():
    sql = RATIO_CTE + """
        SELECT r.gender, COUNT(*) AS people,
               ROUND(AVG(r.arm_to_height), 3)          AS arm_to_height,
               ROUND(AVG(r.leg_to_height), 3)          AS leg_to_height,
               ROUND(AVG(r.waist_to_hip), 3)           AS waist_to_hip,
               ROUND(AVG(r.shoulder_to_chest), 3)      AS shoulder_to_chest,
               ROUND(AVG(r.chest_depth_to_breadth), 3) AS chest_depth_to_breadth
        FROM ratios AS r
        GROUP BY r.gender
        ORDER BY r.gender
    """
    return query(sql)


if __name__ == "__main__":
    show("사람별 신체 비율 (전체)", body_ratios())
    show("사람별 신체 비율 (여성만)", body_ratios("female"))
    show("성별 평균 비율 → 3D 성별 기본 비례", ratio_means_by_gender())
