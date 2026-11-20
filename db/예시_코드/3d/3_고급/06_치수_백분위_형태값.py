# 목적: 한 사람의 치수가 같은 성별 안에서 어디쯤인지(순위·백분위·평균과 차이) → 3D 형태 키(blendshape) 가중치 0~1
# 누가 쓰나: 3D
# 난이도: 고급 — 창 함수(RANK·PERCENT_RANK·COUNT·AVG OVER PARTITION BY) + CTE 로 전체 계산 후 바깥에서 한 사람만 거르기
# 출력: 성별 내 위치 표 3개 — profile 19 몸통(14행)·22 다리(4행)·6 전부(5행); rank_in_gender·shape_weight·diff_from_mean
# 실행: .venv/bin/python db/예시_코드/3d/3_고급/06_치수_백분위_형태값.py
# shape_weight = PERCENT_RANK: 성별 안 가장 작은 값 0, 가장 큰 값 1. 표본이 1명이면 0
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 한 사람의 치수별 성별 내 위치. 창 함수는 WHERE 보다 늦게 계산되므로
#       CTE 안에서 모든 사람으로 계산하고, 바깥 SELECT 에서 profile_id 로 거름
def shape_weights(profile_id, body_part=None):
    sql = """
        WITH ranked AS (
            SELECT md.profile_id, p.gender, md.body_part, md.measure_code, md.korean_name, md.value_cm,
                   RANK() OVER w AS rank_in_gender,
                   COUNT(*) OVER (PARTITION BY p.gender, md.measure_code) AS group_people,
                   ROUND(PERCENT_RANK() OVER w, 2) AS shape_weight,
                   ROUND(md.value_cm - AVG(md.value_cm) OVER (PARTITION BY p.gender, md.measure_code), 1) AS diff_from_mean
            FROM body.measure_details AS md
            JOIN body.profiles AS p ON p.profile_id = md.profile_id
            WINDOW w AS (PARTITION BY p.gender, md.measure_code ORDER BY md.value_cm)
        )
        SELECT r.body_part, r.measure_code, r.korean_name, r.value_cm,
               r.rank_in_gender, r.group_people, r.shape_weight, r.diff_from_mean
        FROM ranked AS r
        WHERE r.profile_id = %s
          AND (%s IS NULL OR r.body_part = %s)
        ORDER BY FIELD(r.body_part, 'full', 'torso', 'arm', 'leg', 'neck'), r.measure_code
    """
    return query(sql, (profile_id, body_part, body_part))


if __name__ == "__main__":
    # profile 19: 더미 회원 2 (여성) — 몸통은 ANSUR II·BodyM 여성까지 표본이 큼
    show("성별 내 위치 — 몸통 (profile_id = 19)", shape_weights(19, "torso"))
    # profile 22: 더미 회원 5 (남성) — 다리
    show("성별 내 위치 — 다리 (profile_id = 22)", shape_weights(22, "leg"))
    # profile 6: ANSUR II 여성 — 가진 치수 전부
    show("성별 내 위치 — 전부 (profile_id = 6)", shape_weights(6))
