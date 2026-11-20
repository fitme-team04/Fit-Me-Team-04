# 목적: 한 사람의 신체 치수를 부위별(키·몸통·팔·다리·목)로 묶고 촬영 자세까지 → 3D 신체 모델 입력 JSON
# 누가 쓰나: 3D
# 난이도: 심화 — 2개 표 JOIN(치수 + 항목 정의, 자세 + 신체 정보) + 부위별 뷰 조회 → JSON
# 출력: 예시 표 2개 + profile 6·18 부위별·자세 표와 3D 입력 JSON(parts·pose); --save 면 out/3d/body_parts_<id>.json
# 실행: .venv/bin/python db/예시_코드/3d/2_심화/06_부위별_신체치수_JSON.py            (JSON 은 화면에 출력)
#       .venv/bin/python db/예시_코드/3d/2_심화/06_부위별_신체치수_JSON.py --save     (out/3d/body_parts_<profile_id>.json 으로도 저장)
# JSON 은 3D 신체 모델(anny·clad_body 등)에 넣을 목표 치수로 씀. 단위는 cm·도(deg)
import json
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show, save_text

# 부위 → 조회할 뷰 (db/sql/40_view_body_part.sql). full(키)은 뷰가 없어 measure_details 에서 거름
PART_VIEWS = {
    "torso": "body.torso_measures",
    "arm": "body.arm_measures",
    "leg": "body.leg_measures",
    "neck": "body.neck_measures",
}


# 목적: 신체 정보 한 건 (성별·나이·키·체중)
def profile(profile_id):
    sql = """
        SELECT p.profile_id, p.user_id, p.gender, p.age, p.height_cm, p.weight_kg, p.source_name
        FROM body.profiles AS p
        WHERE p.profile_id = %s
    """
    rows = query(sql, (profile_id,))
    if len(rows) == 0:
        return None
    return rows[0]


# 목적: 부위 하나의 치수 행 목록. 뷰 이름은 위 PART_VIEWS 에 정해 둔 것만 씀 (SQL 에 글자를 직접 넣는 곳이라 고정값만)
def part_measures(profile_id, part):
    if part == "full":
        sql = """
            SELECT t.measure_code, t.korean_name, t.measure_type, t.value_cm, t.measure_method
            FROM body.measure_details AS t
            WHERE t.profile_id = %s AND t.body_part = 'full'
            ORDER BY t.measure_code
        """
    else:
        sql = """
            SELECT t.measure_code, t.korean_name, t.measure_type, t.value_cm, t.measure_method
            FROM """ + PART_VIEWS[part] + """ AS t
            WHERE t.profile_id = %s
            ORDER BY t.measure_code
        """
    return query(sql, (profile_id,))


# 목적: 촬영 자세 (없으면 None)
def pose(profile_id):
    sql = """
        SELECT ps.ref_pose, ps.arm_angle_deg, ps.pelvis_tilt_deg, ps.shoulder_tilt_deg
        FROM body.poses AS ps
        WHERE ps.profile_id = %s
    """
    rows = query(sql, (profile_id,))
    if len(rows) == 0:
        return None
    return rows[0]


# 목적: 한 사람의 치수 전부를 부위·항목 이름과 함께 한 표로 (부위 구분 없이 훑어볼 때)
def all_measures(profile_id):
    sql = """
        SELECT m.measure_code, d.korean_name, d.body_part,
               m.value_cm, m.measure_method, m.model_version
        FROM body.measures AS m
        JOIN ref.measure_definitions AS d ON d.measure_code = m.measure_code
        WHERE m.profile_id = %s
        ORDER BY d.body_part, m.measure_code
    """
    return query(sql, (profile_id,))


# 목적: 기준 자세(A / T)별로 촬영 자세가 있는 사람 목록 (3D 포즈 맞출 대상 고르기)
def poses_by_ref(ref_pose="A"):
    sql = """
        SELECT ps.profile_id, p.user_id, p.gender, ps.ref_pose,
               ps.arm_angle_deg, ps.pelvis_tilt_deg, ps.shoulder_tilt_deg
        FROM body.poses AS ps
        JOIN body.profiles AS p ON p.profile_id = ps.profile_id
        WHERE ps.ref_pose = %s
        ORDER BY ps.profile_id
    """
    return query(sql, (ref_pose,))


# 목적: DB 값(Decimal) → JSON 에 넣을 수 있는 float (NULL 은 None)
def to_number(value):
    if value is None:
        return None
    return float(value)


# 목적: 3D 팀용 묶음 dict 만들기 (화면 표도 같이 출력)
def body_parts(profile_id, verbose=True):
    info = profile(profile_id)
    if info is None:
        print("  (profile_id = " + str(profile_id) + " 없음)")
        return None

    data = {
        "profile_id": info["profile_id"],
        "gender": info["gender"],
        "age": info["age"],
        "height_cm": to_number(info["height_cm"]),
        "weight_kg": to_number(info["weight_kg"]),
        "source_name": info["source_name"],
        "unit": "cm",
        "parts": {},
        "pose": None,
    }

    for part in ["full", "torso", "arm", "leg", "neck"]:
        rows = part_measures(profile_id, part)
        values = {}
        for row in rows:
            values[row["measure_code"]] = to_number(row["value_cm"])
        data["parts"][part] = values
        if verbose:
            show(part + " 치수 (profile_id = " + str(profile_id) + ")", rows)

    p = pose(profile_id)
    if p is not None:
        data["pose"] = {
            "ref_pose": p["ref_pose"],
            "arm_angle_deg": to_number(p["arm_angle_deg"]),
            "pelvis_tilt_deg": to_number(p["pelvis_tilt_deg"]),
            "shoulder_tilt_deg": to_number(p["shoulder_tilt_deg"]),
        }
    if verbose:
        if p is None:
            show("촬영 자세 (profile_id = " + str(profile_id) + ")", [])
        else:
            show("촬영 자세 (profile_id = " + str(profile_id) + ")", [p])
    return data


# 목적: 실행 예시 하나: 표 → JSON 출력 → (--save 면) 파일 저장
def demo(profile_id, save):
    data = body_parts(profile_id)
    if data is None:
        return
    text = json.dumps(data, ensure_ascii=False, indent=2)
    print()
    print("■ 3D 입력 JSON (profile_id = " + str(profile_id) + ")")
    print(text)
    if save:
        path = save_text("3d/body_parts_" + str(profile_id) + ".json", text)
        print("  → 저장: " + str(path))


if __name__ == "__main__":
    save = "--save" in sys.argv
    show("한 사람의 치수 전부 (profile_id = 1)", all_measures(1))
    show("촬영 자세가 있는 사람 (ref_pose = A)", poses_by_ref("A"))
    # profile 6: ANSUR II 여성, 키·몸통 치수 있음 (예시 DB 에 팔·다리·목 치수는 아직 없음 → 빈 {})
    demo(6, save)
    # profile 18: 사용자 1 의 신체 정보, 부위별 치수 23개 + 촬영 자세(A 포즈)
    demo(18, save)
