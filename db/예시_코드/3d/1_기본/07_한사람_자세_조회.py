# 목적: 한 사람의 촬영 자세 하나 조회, 없으면 3D 기본 자세(A 포즈 45도)로 채우기
# 누가 쓰나: 3D
# 난이도: 기본 — 표 1개(body.poses) 기본키로 한 행 SELECT + 파이썬 기본값
# 출력: profile 20·19(db)·1(기록 없음→기본값) 자세 표 각 1행(ref_pose·arm_angle_deg·pelvis/shoulder_tilt_deg·from)
# 실행: .venv/bin/python db/예시_코드/3d/1_기본/07_한사람_자세_조회.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show

# 자세 기록이 없는 사람에게 쓸 3D 기본 자세 (팀 약속값 예시)
DEFAULT_POSE = {"ref_pose": "A", "arm_angle_deg": 45.0, "pelvis_tilt_deg": 0.0, "shoulder_tilt_deg": 0.0}


# 목적: 한 사람의 자세 한 행 (없으면 None)
def pose_of(profile_id):
    sql = """
        SELECT ps.profile_id, ps.ref_pose, ps.arm_angle_deg, ps.pelvis_tilt_deg, ps.shoulder_tilt_deg
        FROM body.poses AS ps
        WHERE ps.profile_id = %s
    """
    rows = query(sql, (profile_id,))
    if len(rows) == 0:
        return None
    return rows[0]


# 목적: 3D 에 넘길 자세 — DB 값이 있으면 그대로(from_db), 없으면 기본 자세(default)
def pose_for_3d(profile_id):
    row = pose_of(profile_id)
    if row is None:
        result = {"profile_id": profile_id}
        for key in DEFAULT_POSE:
            result[key] = DEFAULT_POSE[key]
        result["from"] = "default"
        return result
    row["from"] = "db"
    return row


if __name__ == "__main__":
    # profile 20: T 포즈 기록 있음
    show("자세 (profile_id = 20)", [pose_for_3d(20)])
    # profile 19: A 포즈, 골반·어깨가 조금 기울어짐
    show("자세 (profile_id = 19)", [pose_for_3d(19)])
    # profile 1: ANSUR II 행 — 자세 기록 없음 → 기본 자세
    show("자세 (profile_id = 1, 기록 없음 → 기본값)", [pose_for_3d(1)])
