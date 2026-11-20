# 목적: 한 사람 → 3D 신체 모델 입력 JSON 을 SQL 한 번으로: 부위별 치수 + 체형(body_type) + 비율 + 자세(없으면 기본 A 포즈) + 빠진 필수 치수
# 누가 쓰나: 3D
# 난이도: 고급 — CTE 3개 + 5개 표·뷰(profiles·measures·measure_details·poses·measure_definitions) + JSON 중첩 조립 + EXISTS·NOT EXISTS
# 출력: profile 19·21·6 요약 표(각 1행) + 3D 신체 입력 JSON(parts·ratios·pose·missing_3d); --save 면 out/3d/body_input_<id>.json
# 실행: .venv/bin/python db/예시_코드/3d/3_고급/10_3D신체입력_JSON.py            (JSON 은 화면에 출력)
#       .venv/bin/python db/예시_코드/3d/3_고급/10_3D신체입력_JSON.py --save     (out/3d/body_input_<profile_id>.json 으로도 저장)
# 2_심화/06_부위별_신체치수_JSON.py 는 쿼리 여러 번 + 파이썬 조립. 여기는 체형·비율·누락까지 SQL 이 한 번에 조립
import json
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show, save_text

# 3D 필수 치수 (2_심화/05_3D필수세트_보유자.py 와 같은 약속값)
REQUIRED_3D = ("height", "chest_girth", "waist_girth", "hip_girth", "shoulder_width",
               "arm_length", "inseam", "neck_girth", "thigh_girth", "upperarm_girth")

# MySQL 은 JSON 키를 자기 순서로 정렬함 → 이 순서로 다시 놓음
KEY_ORDER = ["profile_id", "gender", "age", "height_cm", "weight_kg", "body_type", "source_name", "unit",
             "parts", "ratios", "pose", "pose_source", "missing_3d"]


# 목적: %s 자리 n 개를 쉼표로 이은 글자 — IN 목록도 값은 %s 로 넘김
def placeholders(n):
    marks = []
    for i in range(n):
        marks.append("%s")
    return ", ".join(marks)


# 목적: 한 사람의 3D 입력 JSON 을 SQL 로 만들어 dict 로 (사람이 없거나 치수가 하나도 없으면 None)
def body_input(profile_id):
    sql = """
        WITH person AS (
            SELECT p.profile_id, p.gender, p.age, p.height_cm, p.weight_kg, p.body_type, p.source_name
            FROM body.profiles AS p
            WHERE p.profile_id = %s
              AND EXISTS (SELECT 1 FROM body.measures AS m0 WHERE m0.profile_id = p.profile_id)
        ),
        part_values AS (
            SELECT md.body_part, JSON_OBJECTAGG(md.measure_code, md.value_cm) AS vals
            FROM body.measure_details AS md
            JOIN person AS pr ON pr.profile_id = md.profile_id
            GROUP BY md.body_part
        ),
        wide AS (
            SELECT MAX(CASE WHEN m.measure_code = 'height'         THEN m.value_cm END) AS height,
                   MAX(CASE WHEN m.measure_code = 'arm_length'     THEN m.value_cm END) AS arm_length,
                   MAX(CASE WHEN m.measure_code = 'inseam'         THEN m.value_cm END) AS inseam,
                   MAX(CASE WHEN m.measure_code = 'waist_girth'    THEN m.value_cm END) AS waist_girth,
                   MAX(CASE WHEN m.measure_code = 'hip_girth'      THEN m.value_cm END) AS hip_girth,
                   MAX(CASE WHEN m.measure_code = 'shoulder_width' THEN m.value_cm END) AS shoulder_width,
                   MAX(CASE WHEN m.measure_code = 'chest_breadth'  THEN m.value_cm END) AS chest_breadth
            FROM body.measures AS m
            JOIN person AS pr ON pr.profile_id = m.profile_id
        )
        SELECT JSON_OBJECT(
            'profile_id', pr.profile_id, 'gender', pr.gender, 'age', pr.age,
            'height_cm', pr.height_cm, 'weight_kg', pr.weight_kg,
            'body_type', pr.body_type, 'source_name', pr.source_name, 'unit', 'cm',
            'parts', (SELECT JSON_OBJECTAGG(pv.body_part, pv.vals) FROM part_values AS pv),
            'ratios', JSON_OBJECT(
                'arm_to_height',     ROUND(w.arm_length     / NULLIF(COALESCE(w.height, pr.height_cm), 0), 3),
                'leg_to_height',     ROUND(w.inseam         / NULLIF(COALESCE(w.height, pr.height_cm), 0), 3),
                'waist_to_hip',      ROUND(w.waist_girth    / NULLIF(w.hip_girth, 0), 3),
                'shoulder_to_chest', ROUND(w.shoulder_width / NULLIF(w.chest_breadth, 0), 3)),
            'pose', COALESCE(
                (SELECT JSON_OBJECT('ref_pose', ps.ref_pose, 'arm_angle_deg', ps.arm_angle_deg,
                                    'pelvis_tilt_deg', ps.pelvis_tilt_deg, 'shoulder_tilt_deg', ps.shoulder_tilt_deg)
                 FROM body.poses AS ps WHERE ps.profile_id = pr.profile_id),
                JSON_OBJECT('ref_pose', 'A', 'arm_angle_deg', 45.0, 'pelvis_tilt_deg', 0.0, 'shoulder_tilt_deg', 0.0)),
            'pose_source', IF(EXISTS (SELECT 1 FROM body.poses AS ps2 WHERE ps2.profile_id = pr.profile_id),
                              'db', 'default'),
            'missing_3d', COALESCE(
                (SELECT JSON_ARRAYAGG(d.measure_code)
                 FROM ref.measure_definitions AS d
                 WHERE d.measure_code IN (""" + placeholders(len(REQUIRED_3D)) + """)
                   AND NOT EXISTS (SELECT 1 FROM body.measures AS m2
                                   WHERE m2.profile_id = pr.profile_id AND m2.measure_code = d.measure_code)),
                JSON_ARRAY())
        ) AS doc
        FROM person AS pr
        CROSS JOIN wide AS w
    """
    params = [profile_id]
    for code in REQUIRED_3D:
        params.append(code)
    rows = query(sql, tuple(params))
    if len(rows) == 0:
        return None
    raw = json.loads(rows[0]["doc"])
    ordered = {}
    for key in KEY_ORDER:
        ordered[key] = raw.get(key)
    return ordered


# 목적: 화면 확인용 한 줄 요약 (부위별 치수 개수·체형·자세 출처·빠진 수)
def summary_row(doc):
    part_tally = {}
    for part in doc["parts"]:
        part_tally[part] = len(doc["parts"][part])
    return {"profile_id": doc["profile_id"], "gender": doc["gender"], "body_type": doc["body_type"],
            "parts": str(part_tally), "pose": doc["pose"]["ref_pose"], "pose_source": doc["pose_source"],
            "missing_3d": len(doc["missing_3d"])}


# 목적: 실행 예시 하나: 요약 표 → JSON 출력 → (--save 면) 파일 저장
def demo(profile_id, save):
    doc = body_input(profile_id)
    if doc is None:
        print("  (profile_id = " + str(profile_id) + " 없음 또는 치수 없음)")
        return
    show("3D 입력 요약 (profile_id = " + str(profile_id) + ")", [summary_row(doc)])
    text = json.dumps(doc, ensure_ascii=False, indent=2)
    print()
    print("■ 3D 신체 입력 JSON (profile_id = " + str(profile_id) + ")")
    print(text)
    if save:
        path = save_text("3d/body_input_" + str(profile_id) + ".json", text)
        print("  → 저장: " + str(path))


if __name__ == "__main__":
    save = "--save" in sys.argv
    # profile 19: 23항목 + A 포즈 기록 (obese_1)
    demo(19, save)
    # profile 21: 23항목, 자세 기록 없음 → 기본 A 포즈 (underweight)
    demo(21, save)
    # profile 6: ANSUR II 여성 — 몸통 5항목뿐 → missing_3d 에 빠진 필수 치수
    demo(6, save)
