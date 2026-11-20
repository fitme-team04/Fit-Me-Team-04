# 목적: 촬영 자세 + 신체 정보(성별·키·체형)를 한 행으로, 기준 자세(A/T)별 평균 각도 (3D 포즈 리그 기본값 정하기)
# 누가 쓰나: 3D
# 난이도: 심화 — 2개 표 JOIN(body.poses + body.profiles) + GROUP BY + COUNT·AVG·MIN·MAX
# 출력: 자세+신체 정보 표(3행; gender·height_cm·body_type·ref_pose·arm_angle_deg 등) + 기준 자세별 요약 표(A·T 2행)
# 실행: .venv/bin/python db/예시_코드/3d/2_심화/03_자세_신체정보_결합.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 자세가 있는 사람의 자세 + 신체 정보
def poses_with_profile():
    sql = """
        SELECT ps.profile_id, p.gender, p.height_cm, p.body_type,
               ps.ref_pose, ps.arm_angle_deg, ps.pelvis_tilt_deg, ps.shoulder_tilt_deg
        FROM body.poses AS ps
        JOIN body.profiles AS p ON p.profile_id = ps.profile_id
        ORDER BY ps.ref_pose, ps.profile_id
    """
    return query(sql)


# 목적: 기준 자세별 사람 수와 팔 각도 평균·범위, 평균 키
def pose_summary():
    sql = """
        SELECT ps.ref_pose, COUNT(*) AS people,
               ROUND(AVG(ps.arm_angle_deg), 1) AS avg_arm_angle,
               MIN(ps.arm_angle_deg) AS min_arm_angle,
               MAX(ps.arm_angle_deg) AS max_arm_angle,
               ROUND(AVG(p.height_cm), 1) AS avg_height_cm
        FROM body.poses AS ps
        JOIN body.profiles AS p ON p.profile_id = ps.profile_id
        GROUP BY ps.ref_pose
        ORDER BY ps.ref_pose
    """
    return query(sql)


if __name__ == "__main__":
    show("자세 + 신체 정보", poses_with_profile())
    show("기준 자세별 요약", pose_summary())
