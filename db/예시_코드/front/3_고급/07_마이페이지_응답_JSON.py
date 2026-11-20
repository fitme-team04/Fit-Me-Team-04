# 목적: 마이페이지 API — email 하나로 회원·최근 신체 정보(BMI·체형)·부위별 치수·촬영 자세·이력 수를 한 번에 묶어 응답(JSON)
# 누가 쓰나: 프론트 (화면 조각별 조회는 front/2_심화/05~09)
# 난이도: 고급 — 한 접속에서 여러 쿼리를 이어 부르고 결과를 중첩 JSON 으로 조립 (Decimal·날짜 → JSON 변환 포함)
# 출력: user01 마이페이지 JSON(user·latest_profile·pose·부위별 measures 23개), nobody 는 ok false·errors
# 실행: .venv/bin/python db/예시_코드/front/3_고급/07_마이페이지_응답_JSON.py   (조회만, DB 에 쓰지 않음)
import datetime
import decimal
import json
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import connect, query_in
from _body_type import bmi_of, body_type_name


# 목적: JSON 이 모르는 값 변환 (DECIMAL → float, DATE·DATETIME → 'YYYY-MM-DD...')
def json_default(value):
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    raise TypeError("JSON 으로 못 바꾸는 값: " + repr(value))


# 목적: 생년월일 → 오늘 기준 만 나이 (없으면 None)
def age_of(birth_date):
    if birth_date is None:
        return None
    today = datetime.date.today()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


# 목적: 한 접속에서 profile 의 치수 → {부위: [{"code", "name", "value_cm", "method"}]}
def measures_by_part(conn, profile_id):
    sql = """
        SELECT d.body_part, m.measure_code, d.korean_name, m.value_cm, m.measure_method
        FROM body.measures AS m
        JOIN ref.measure_definitions AS d ON d.measure_code = m.measure_code
        WHERE m.profile_id = %s
        ORDER BY FIELD(d.body_part, 'full', 'neck', 'torso', 'arm', 'leg'), d.korean_name
    """
    groups = {}
    for row in query_in(conn, sql, (profile_id,)):
        part = row["body_part"]
        if part not in groups:
            groups[part] = []
        groups[part].append({"code": row["measure_code"], "name": row["korean_name"],
                             "value_cm": row["value_cm"], "method": row["measure_method"]})
    return groups


# 목적: API 본체: email → 마이페이지 응답 dict
def handle_my_page(email):
    conn = connect()
    try:
        users = query_in(conn, "SELECT user_id, user_name, gender, birth_date, email, created_at "
                               "FROM body.users WHERE email = %s", (email,))
        if len(users) == 0:
            return {"ok": False, "errors": ["가입하지 않은 email: " + email]}
        user = users[0]
        user["age"] = age_of(user["birth_date"])

        profiles = query_in(conn, """
            SELECT p.profile_id, p.height_cm, p.weight_kg, p.body_type, p.created_at,
                   po.ref_pose, po.arm_angle_deg
            FROM body.profiles AS p
            LEFT JOIN body.poses AS po ON po.profile_id = p.profile_id
            WHERE p.user_id = %s
            ORDER BY p.created_at DESC, p.profile_id DESC
        """, (user["user_id"],))

        response = {"ok": True, "user": user, "profile_history_tally": len(profiles),
                    "latest_profile": None, "pose": None, "measures_by_part": {}, "measure_tally": 0}
        if len(profiles) == 0:
            response["message"] = "신체 정보를 입력하세요"
            return response

        latest = profiles[0]
        bmi = bmi_of(latest["height_cm"], latest["weight_kg"])
        if bmi is not None:
            bmi = round(bmi, 1)
        response["latest_profile"] = {"profile_id": latest["profile_id"], "height_cm": latest["height_cm"],
                                      "weight_kg": latest["weight_kg"], "bmi": bmi,
                                      "body_type": latest["body_type"],
                                      "body_type_name": body_type_name(latest["body_type"]),
                                      "created_at": latest["created_at"]}
        if latest["ref_pose"] is not None:
            response["pose"] = {"ref_pose": latest["ref_pose"], "arm_angle_deg": latest["arm_angle_deg"]}
        groups = measures_by_part(conn, latest["profile_id"])
        tally = 0
        for part in groups:
            tally += len(groups[part])
        response["measures_by_part"] = groups
        response["measure_tally"] = tally
        return response
    finally:
        conn.close()


if __name__ == "__main__":
    for email in ["user01@example.com", "nobody@example.com"]:
        print()
        print("■ 마이페이지 응답 (email = " + email + ")")
        print(json.dumps(handle_my_page(email), ensure_ascii=False, indent=2, default=json_default))
