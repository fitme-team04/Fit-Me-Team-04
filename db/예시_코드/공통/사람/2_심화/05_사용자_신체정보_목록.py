# 목적: 사용자 + 신체 정보(키·체중·BMI·체형) 목록, 출처(source_name)별·체형(body_type)별 사람 수
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 심화 — 2개 표 LEFT JOIN(사용자 + 신체 정보) + GROUP BY COUNT·AVG. BMI·체형 이름은 파이썬(_body_type.py)
# 출력: 표 3개 — 사용자+신체 정보(키·체중·BMI·체형, 5행), 출처별 사람 수·평균 키·체중(3행), 체형별 사람 수(6행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/2_심화/05_사용자_신체정보_목록.py
# 체형(body_type)은 대한비만학회 BMI 단계 (underweight ~ obese_3), 한글 이름은 _body_type.py 의 BODY_TYPE_NAMES
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show
from _body_type import BODY_TYPES, bmi_of, body_type_name      # 체형 허용값·BMI·한글 이름


# 목적: 사용자마다 신체 정보 (신체 정보가 없는 사용자도 나오도록 LEFT JOIN) + 파이썬으로 BMI·체형 한글 이름
def users_with_profile():
    sql = """
        SELECT u.user_id, u.user_name, u.gender,
               p.profile_id, p.height_cm, p.weight_kg, p.body_type
        FROM body.users AS u
        LEFT JOIN body.profiles AS p ON p.user_id = u.user_id
        ORDER BY u.user_id, p.profile_id
    """
    rows = query(sql)
    for row in rows:
        bmi = bmi_of(row["height_cm"], row["weight_kg"])
        if bmi is None:
            row["bmi"] = None
        else:
            row["bmi"] = round(bmi, 1)
        row["체형"] = body_type_name(row["body_type"])
    return rows


# 목적: 출처(ansur2 / bodym / user)별 사람 수·회원 수·평균 키·평균 체중
def people_by_source():
    sql = """
        SELECT p.source_name,
               COUNT(*) AS people_tally,
               COUNT(p.user_id) AS member_tally,
               ROUND(AVG(p.height_cm), 1) AS avg_height_cm,
               ROUND(AVG(p.weight_kg), 1) AS avg_weight_kg
        FROM body.profiles AS p
        GROUP BY p.source_name
        ORDER BY p.source_name
    """
    return query(sql)


# 목적: 체형별 사람 수 (BMI 작은 단계부터, 아무도 없는 단계도 0 으로 보여 줌)
def people_by_body_type():
    sql = """
        SELECT p.body_type, COUNT(*) AS people_tally
        FROM body.profiles AS p
        GROUP BY p.body_type
    """
    tally = {}
    for row in query(sql):
        tally[row["body_type"]] = row["people_tally"]
    result = []
    for body_type in BODY_TYPES:                 # 정해 둔 순서로 다시 줄 세우기
        count = 0
        if body_type in tally:
            count = tally[body_type]
        result.append({"body_type": body_type, "체형": body_type_name(body_type), "people_tally": count})
    return result


if __name__ == "__main__":
    show("사용자 + 신체 정보 (BMI·체형은 파이썬 계산)", users_with_profile())
    show("출처별 사람 수 (body.profiles)", people_by_source())
    show("체형별 사람 수 (body_type)", people_by_body_type())
