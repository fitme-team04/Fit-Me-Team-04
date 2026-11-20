# 목적: "내 정보" 화면의 촬영 자세 칸 — email 로 신체 정보마다 기준 자세(A/T)·팔 각도가 있는지, 없으면 "다시 촬영" 안내
# 누가 쓰나: 프론트
# 난이도: 심화 — 3개 표 JOIN + LEFT JOIN (users · profiles · poses, 자세가 없어도 신체 정보 행은 나옴)
# 출력: user01·03·04 촬영 자세 각 1행(ref_pose A·T·NULL, 각도), 기록 없으면 다시 촬영 안내 message
# 실행: .venv/bin/python db/예시_코드/front/2_심화/09_내_촬영자세_조회.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show

POSE_NAMES = {"A": "A 자세 (팔을 비스듬히)", "T": "T 자세 (팔을 옆으로)"}


# 목적: email 의 신체 정보마다 촬영 자세 (자세 기록이 없으면 ref_pose 가 NULL)
def my_poses(email):
    sql = """
        SELECT p.profile_id, p.created_at, po.ref_pose, po.arm_angle_deg, po.shoulder_tilt_deg, po.pelvis_tilt_deg
        FROM body.users AS u
        JOIN body.profiles AS p ON p.user_id = u.user_id
        LEFT JOIN body.poses AS po ON po.profile_id = p.profile_id
        WHERE u.email = %s
        ORDER BY p.created_at DESC, p.profile_id DESC
    """
    return query(sql, (email,))


# 목적: 자세 행 → 화면 문구 한 줄
def pose_message(row):
    if row["ref_pose"] is None:
        return "자세 기록 없음 → 사진을 다시 촬영하면 3D 모델이 정확해짐"
    return POSE_NAMES.get(row["ref_pose"], row["ref_pose"]) + ", 팔 " + str(row["arm_angle_deg"]) + "도"


if __name__ == "__main__":
    for email in ["user01@example.com", "user03@example.com", "user04@example.com"]:
        rows = my_poses(email)
        for row in rows:
            row["message"] = pose_message(row)
        show("촬영 자세 (email = " + email + ")", rows)
