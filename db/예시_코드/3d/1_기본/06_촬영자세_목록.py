# 목적: 촬영 자세(body.poses) 전체 목록과 팔 각도 범위로 거르기 (3D 모델을 A·T 포즈로 세울 각도 확인)
# 누가 쓰나: 3D
# 난이도: 기본 — 표 1개(body.poses) SELECT + WHERE BETWEEN·ORDER BY
# 출력: body.poses 표 3개 — 전체(3행)·팔 각도 30~60도 A(2행)·80~100도 T(1행); profile_id·ref_pose·arm_angle_deg 등
# 실행: .venv/bin/python db/예시_코드/3d/1_기본/06_촬영자세_목록.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 자세 전체 (기준 자세 A/T, 팔 각도, 골반·어깨 기울기)
def all_poses():
    sql = """
        SELECT ps.profile_id, ps.ref_pose, ps.arm_angle_deg, ps.pelvis_tilt_deg, ps.shoulder_tilt_deg
        FROM body.poses AS ps
        ORDER BY ps.ref_pose, ps.profile_id
    """
    return query(sql)


# 목적: 팔 각도(몸통과 팔 사이, 도)가 범위 안인 자세만 (A 포즈 ≈ 30~60도, T 포즈 ≈ 90도)
def poses_by_arm_angle(min_deg, max_deg):
    sql = """
        SELECT ps.profile_id, ps.ref_pose, ps.arm_angle_deg
        FROM body.poses AS ps
        WHERE ps.arm_angle_deg BETWEEN %s AND %s
        ORDER BY ps.arm_angle_deg
    """
    return query(sql, (min_deg, max_deg))


if __name__ == "__main__":
    show("촬영 자세 전체 (body.poses)", all_poses())
    show("팔 각도 30~60도 (A 포즈 범위)", poses_by_arm_angle(30, 60))
    show("팔 각도 80~100도 (T 포즈 범위)", poses_by_arm_angle(80, 100))
