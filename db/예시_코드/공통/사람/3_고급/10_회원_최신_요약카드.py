# 목적: 회원 1명 = 1행 요약 카드 — 가장 최근 신체 정보 + BMI 단계 + 주요 치수(가슴·허리·엉덩이) + 부위별 치수 수 + 촬영 자세 유무 → JSON
# 누가 쓰나: 공통 (프론트 회원 상세 화면, 3D·AI 가 회원 한 명을 고를 때)
# 난이도: 고급 — 창 함수 ROW_NUMBER(최신 1건) CTE + 5개 표(사용자·신체 정보·치수·항목 정의·자세) JOIN + 피벗 + BMI CASE + EXISTS
# 출력: 표 2개 — 회원 요약 카드(BMI·체형·가슴/허리/엉덩이·치수 수, 5행), 회원 4(1행) + JSON 5건(--save: out/사람/member_cards.json)
# 실행: .venv/bin/python db/예시_코드/공통/사람/3_고급/10_회원_최신_요약카드.py            (JSON 은 화면에 출력)
#       .venv/bin/python db/예시_코드/공통/사람/3_고급/10_회원_최신_요약카드.py --save     (out/사람/member_cards.json 으로도 저장)
# 체형 기준: 대한비만학회 BMI 단계 (_body_type.py). 저장된 body_type 과 SQL 계산 bmi_type 을 같이 보여 줌
import json
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show, save_text
from _body_type import body_type_name                          # body_type → 한글 이름


# 목적: 회원마다 최신 신체 정보 1건 기준 요약 (user_id 를 주면 그 회원만, None 이면 전체)
def member_cards(user_id=None):
    sql = """
        WITH latest AS (
            SELECT p.profile_id, p.user_id, p.age, p.height_cm, p.weight_kg, p.body_type, p.created_at,
                   ROW_NUMBER() OVER (PARTITION BY p.user_id ORDER BY p.created_at DESC, p.profile_id DESC) AS row_no
            FROM body.profiles AS p
            WHERE p.user_id IS NOT NULL
        ),
        key_measures AS (
            SELECT m.profile_id,
                   MAX(CASE WHEN m.measure_code = 'chest_girth' THEN m.value_cm END) AS chest_cm,
                   MAX(CASE WHEN m.measure_code = 'waist_girth' THEN m.value_cm END) AS waist_cm,
                   MAX(CASE WHEN m.measure_code = 'hip_girth'   THEN m.value_cm END) AS hip_cm,
                   SUM(CASE WHEN d.body_part = 'torso' THEN 1 ELSE 0 END) AS torso_tally,
                   SUM(CASE WHEN d.body_part = 'arm'   THEN 1 ELSE 0 END) AS arm_tally,
                   SUM(CASE WHEN d.body_part = 'leg'   THEN 1 ELSE 0 END) AS leg_tally,
                   COUNT(*) AS measure_tally
            FROM body.measures AS m
            JOIN ref.measure_definitions AS d ON d.measure_code = m.measure_code
            GROUP BY m.profile_id
        )
        SELECT u.user_id, u.user_name, u.gender, u.email,
               TIMESTAMPDIFF(YEAR, u.birth_date, CURDATE()) AS age_now,
               l.profile_id, l.height_cm, l.weight_kg,
               ROUND(l.weight_kg / POW(l.height_cm / 100, 2), 1) AS bmi,
               CASE
                   WHEN l.weight_kg / POW(l.height_cm / 100, 2) < 18.5 THEN 'underweight'
                   WHEN l.weight_kg / POW(l.height_cm / 100, 2) < 23   THEN 'normal'
                   WHEN l.weight_kg / POW(l.height_cm / 100, 2) < 25   THEN 'pre_obese'
                   WHEN l.weight_kg / POW(l.height_cm / 100, 2) < 30   THEN 'obese_1'
                   WHEN l.weight_kg / POW(l.height_cm / 100, 2) < 35   THEN 'obese_2'
                   ELSE 'obese_3'
               END AS bmi_type,
               l.body_type,
               k.chest_cm, k.waist_cm, k.hip_cm,
               k.torso_tally, k.arm_tally, k.leg_tally, k.measure_tally,
               CASE WHEN EXISTS (SELECT 1 FROM body.poses AS ps WHERE ps.profile_id = l.profile_id)
                    THEN 'Y' ELSE 'N' END AS has_pose
        FROM body.users AS u
        JOIN latest AS l ON l.user_id = u.user_id AND l.row_no = 1
        LEFT JOIN key_measures AS k ON k.profile_id = l.profile_id
        WHERE (%s IS NULL OR u.user_id = %s)
        ORDER BY u.user_id
    """
    return query(sql, (user_id, user_id))


# 목적: DB 값(Decimal·날짜) → JSON 에 넣을 수 있는 값 (숫자는 float, 그 밖은 그대로 또는 글자)
def to_json_value(value):
    if value is None:
        return None
    if isinstance(value, (int, float, str)):
        return value
    text = str(value)
    try:
        return float(text)
    except ValueError:
        return text


# 목적: 표 행 → 카드 dict 목록 (한글 체형 이름 추가)
def to_cards(rows):
    cards = []
    for row in rows:
        card = {}
        for key in row:
            card[key] = to_json_value(row[key])
        card["체형"] = body_type_name(row["body_type"])
        cards.append(card)
    return cards


if __name__ == "__main__":
    save = "--save" in sys.argv
    rows = member_cards(None)
    show("회원 요약 카드 (최신 신체 정보 기준)", rows)
    show("회원 4 의 요약 카드", member_cards(4))
    text = json.dumps(to_cards(rows), ensure_ascii=False, indent=2)
    print()
    print("■ 회원 요약 카드 JSON")
    print(text)
    if save:
        path = save_text("사람/member_cards.json", text)
        print("  → 저장: " + str(path))
