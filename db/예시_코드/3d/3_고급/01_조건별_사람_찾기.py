# 목적: 조건(성별·나이대·체형·BMI·키 범위)에 맞는 사람들의 신체 정보 찾기 (예: 1단계 비만 체형 20대 여성)
# 누가 쓰나: 3D (체형별 대표 몸 모델 고르기). AI 데이터 살펴보기에도 씀
# 난이도: 고급 — 3개 표 LEFT JOIN + SQL 계산식(BMI) + 선택 조건 (%s IS NULL OR ...) 9개
# 출력: 조건 3개(20대 obese_1 여성 3명·BMI≥25 여성 8명·키 155~170 여성 7명)마다 사람 표(age·bmi·체형 등) + 신체 치수 표
# 실행: .venv/bin/python db/예시_코드/3d/3_고급/01_조건별_사람_찾기.py
# 체형 기준: 대한비만학회(KSSO) — 한국 성인 BMI 25 kg/m² 이상 = 비만 (23~24.9 비만 전단계, 25~29.9 1단계 비만)
#   https://general.kosso.or.kr/html/?pmode=BBBS0001300004&smode=view&seq=1429 (비만 진단기준 성명서 2024-11-20, BMI 25 유지)
#   https://general.kosso.or.kr/html/user/core/view/reaction/main/kosso/inc/data/guideline2022_vol8.pdf (비만 진료지침 2022 요약본 표 1)
#   체형 값(body_type: underweight ~ obese_3)은 body.profiles 컬럼, 계산 규칙은 _body_type.py
# 주의: BodyM 행은 나이(age)가 없음(NULL) → 나이 조건을 주면 BodyM 사람은 빠짐
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show
from _body_type import body_type_name                          # body_type → 한글 이름

OBESITY_BMI = 25.0     # 대한비만학회 비만 기준 (kg/m²)


# 목적: 조건에 맞는 사람 + 치수 행 (BMI = 체중 kg / (키 m)², SQL 에서 계산). None 인 조건은 안 씀
# body_type 은 저장된 체형 값(obese_1 등)으로 거름
def find_rows(gender, age_min, age_max, bmi_min, bmi_max, height_min, height_max, body_type):
    sql = """
        SELECT p.profile_id, p.user_id, p.source_name, p.gender, p.age, p.height_cm, p.weight_kg,
               ROUND(p.weight_kg / POW(p.height_cm / 100, 2), 1) AS bmi, p.body_type,
               m.measure_code, d.korean_name, m.value_cm, m.measure_method
        FROM body.profiles AS p
        LEFT JOIN body.measures AS m ON m.profile_id = p.profile_id
        LEFT JOIN ref.measure_definitions AS d ON d.measure_code = m.measure_code
        WHERE p.gender = %s
          AND p.height_cm IS NOT NULL AND p.weight_kg IS NOT NULL
          AND (%s IS NULL OR p.age >= %s)
          AND (%s IS NULL OR p.age <= %s)
          AND (%s IS NULL OR p.weight_kg / POW(p.height_cm / 100, 2) >= %s)
          AND (%s IS NULL OR p.weight_kg / POW(p.height_cm / 100, 2) <  %s)
          AND (%s IS NULL OR p.height_cm >= %s)
          AND (%s IS NULL OR p.height_cm <= %s)
          AND (%s IS NULL OR p.body_type = %s)
        ORDER BY p.profile_id, m.measure_code
    """
    params = (gender, age_min, age_min, age_max, age_max, bmi_min, bmi_min, bmi_max, bmi_max,
              height_min, height_min, height_max, height_max, body_type, body_type)
    return query(sql, params)


# 목적: 사람별로 묶기 → [{"profile_id", ..., "bmi", "body_type", "measures": {코드: 값}, "measure_names": {코드: 한글}}]
def find_profiles(gender, age_min, age_max, bmi_min=None, bmi_max=None, height_min=None, height_max=None,
                  body_type=None):
    people = []
    by_id = {}
    for row in find_rows(gender, age_min, age_max, bmi_min, bmi_max, height_min, height_max, body_type):
        pid = row["profile_id"]
        if pid not in by_id:
            item = {"profile_id": pid, "user_id": row["user_id"], "source_name": row["source_name"],
                    "gender": row["gender"], "age": row["age"], "height_cm": row["height_cm"],
                    "weight_kg": row["weight_kg"], "bmi": row["bmi"], "body_type": row["body_type"],
                    "measures": {}, "measure_names": {}}
            by_id[pid] = item
            people.append(item)
        if row["measure_code"] is not None:
            by_id[pid]["measures"][row["measure_code"]] = row["value_cm"]
            by_id[pid]["measure_names"][row["measure_code"]] = row["korean_name"]
    return people


# 목적: 사람 표 + 치수 표 출력 (체형 한글 이름은 _body_type.py)
def print_people(title, people):
    summary = []
    details = []
    for p in people:
        summary.append({"profile_id": p["profile_id"], "user_id": p["user_id"], "source_name": p["source_name"],
                        "age": p["age"], "height_cm": p["height_cm"], "weight_kg": p["weight_kg"], "bmi": p["bmi"],
                        "body_type": p["body_type"], "체형": body_type_name(p["body_type"]),
                        "measure_tally": len(p["measures"])})
        for code in p["measures"]:
            details.append({"profile_id": p["profile_id"], "measure_code": code,
                            "korean_name": p["measure_names"][code], "value_cm": p["measures"][code]})
    show(title, summary)
    if len(people) == 0:
        print("  → 조건에 맞는 사람 없음 (예시 DB 는 사람이 22명뿐)")
        return
    show(title + " — 신체 치수", details)


if __name__ == "__main__":
    # 1) 저장된 체형 값으로: 1단계 비만(obese_1) 20대 여성 — 더미 회원(source_name = user)도 나옴
    people = find_profiles("female", 20, 29, body_type="obese_1")
    print_people("1단계 비만 20대 여성 (female, 20~29세, body_type = obese_1)", people)
    if len(people) == 0:
        print("  → 아래 2) 에서 나이 조건을 빼고 다시 찾음")

    # 2) BMI 숫자로 넓혀서: 나이 무관 비만(BMI ≥ 25) 여성 — BodyM(나이 없음) 사람도 포함됨
    print_people("비만 체형 여성 (나이 무관, BMI ≥ 25, BodyM 포함)", find_profiles("female", None, None, bmi_min=OBESITY_BMI))

    # 3) 키 범위만 (성별 + 키 155~170cm)
    print_people("여성 키 155~170cm (나이·BMI 무관)", find_profiles("female", None, None, height_min=155, height_max=170))
