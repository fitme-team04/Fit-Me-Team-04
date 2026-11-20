# 목적: 성별마다 평균 몸(가슴·허리·엉덩이 둘레)에 가장 가까운 사람 고르기 → 3D 대표 몸(기본 아바타) 후보
# 누가 쓰나: 3D
# 난이도: 고급 — CTE 4단계(피벗 → 창 함수 AVG OVER → 거리 계산식 SQRT·POW → ROW_NUMBER) + 바깥 WHERE 로 위 N명
# 출력: 성별 대표 몸 표 — 1명(2행)·후보 3명(6행); pick·profile_id·chest·waist·hip·성별 평균(*_mean)·distance_cm
# 실행: .venv/bin/python db/예시_코드/3d/3_고급/08_성별_대표몸_고르기.py
# 거리 = √((가슴−평균)² + (허리−평균)² + (엉덩이−평균)²), 단위 cm. 작을수록 평균 몸에 가까움
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 성별마다 평균에 가까운 순서로 위 top_n 명 (세 둘레가 모두 있는 사람만)
def representative_bodies(top_n):
    sql = """
        WITH wide AS (
            SELECT m.profile_id,
                   MAX(CASE WHEN m.measure_code = 'chest_girth' THEN m.value_cm END) AS chest,
                   MAX(CASE WHEN m.measure_code = 'waist_girth' THEN m.value_cm END) AS waist,
                   MAX(CASE WHEN m.measure_code = 'hip_girth'   THEN m.value_cm END) AS hip
            FROM body.measures AS m
            GROUP BY m.profile_id
        ),
        with_mean AS (
            SELECT p.profile_id, p.gender, p.body_type, p.source_name, w.chest, w.waist, w.hip,
                   AVG(w.chest) OVER (PARTITION BY p.gender) AS chest_mean,
                   AVG(w.waist) OVER (PARTITION BY p.gender) AS waist_mean,
                   AVG(w.hip)   OVER (PARTITION BY p.gender) AS hip_mean
            FROM wide AS w
            JOIN body.profiles AS p ON p.profile_id = w.profile_id
            WHERE w.chest IS NOT NULL AND w.waist IS NOT NULL AND w.hip IS NOT NULL
        ),
        scored AS (
            SELECT wm.*,
                   SQRT(POW(wm.chest - wm.chest_mean, 2)
                      + POW(wm.waist - wm.waist_mean, 2)
                      + POW(wm.hip   - wm.hip_mean, 2)) AS distance
            FROM with_mean AS wm
        ),
        ranked AS (
            SELECT sc.*,
                   ROW_NUMBER() OVER (PARTITION BY sc.gender ORDER BY sc.distance, sc.profile_id) AS pick
            FROM scored AS sc
        )
        SELECT r.gender, r.pick, r.profile_id, r.source_name, r.body_type,
               r.chest, r.waist, r.hip,
               ROUND(r.chest_mean, 1) AS chest_mean, ROUND(r.waist_mean, 1) AS waist_mean,
               ROUND(r.hip_mean, 1) AS hip_mean, ROUND(r.distance, 1) AS distance_cm
        FROM ranked AS r
        WHERE r.pick <= %s
        ORDER BY r.gender, r.pick
    """
    return query(sql, (top_n,))


if __name__ == "__main__":
    show("성별 대표 몸 1명", representative_bodies(1))
    show("성별 대표 몸 후보 3명", representative_bodies(3))
