# 목적: 회원가입 화면을 처음 열 때 내려 줄 폼 기본값(JSON) — 칸마다 초기값·필수 여부·선택지·생년월일 달력 범위 (DB 접속 없음)
# 누가 쓰나: 프론트
# 난이도: 기본 — SQL 없음, _검증.py 상수로 dict 만들고 날짜 계산(나이 14~100세 → 생년월일 범위)만
# 출력: 가입 폼 JSON(fields 7개·submit_label, 생년월일 min·max), 빈 제출 오류 6개, 예시 회원 01 오류 0개
# 실행: .venv/bin/python db/예시_코드/front/1_기본/05_가입폼_기본값.py
import datetime
import json
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _검증 import (GENDERS, HEIGHT_MIN, HEIGHT_MAX, WEIGHT_MIN, WEIGHT_MAX, AGE_MIN, AGE_MAX,
                  validate)                           # 허용값·범위 + 입력 검사


# 목적: 오늘에서 years 년 전 날짜 (2월 29일이 없는 해면 2월 28일)
def years_ago(today, years):
    try:
        return today.replace(year=today.year - years)
    except ValueError:
        return today.replace(year=today.year - years, day=28)


# 목적: 생년월일 달력에서 고를 수 있는 범위 (가장 이른 날, 가장 늦은 날) — 만 AGE_MIN ~ AGE_MAX 세
def birth_date_range(today):
    latest = years_ago(today, AGE_MIN)                                   # 이날 이후 태어나면 AGE_MIN 세 미만
    earliest = years_ago(today, AGE_MAX + 1) + datetime.timedelta(days=1)  # 이날 전에 태어나면 AGE_MAX 세 초과
    return earliest.isoformat(), latest.isoformat()


# 목적: 가입 폼 기본값 전체 (화면이 이 JSON 하나로 칸을 그림)
def signup_form_defaults(today):
    earliest, latest = birth_date_range(today)
    gender_choices = []
    for gender in GENDERS:
        gender_choices.append(gender)
    return {
        "fields": [
            {"name": "user_name", "value": "", "required": True, "max_length": 50},
            {"name": "email", "value": "", "required": True, "max_length": 100, "check": "형식 → 중복 확인 버튼"},
            {"name": "gender", "value": "", "required": True, "choices": gender_choices},
            {"name": "birth_date", "value": "", "required": True, "min": earliest, "max": latest},
            {"name": "height_cm", "value": "", "required": True, "min": HEIGHT_MIN, "max": HEIGHT_MAX, "step": 0.1},
            {"name": "weight_kg", "value": "", "required": True, "min": WEIGHT_MIN, "max": WEIGHT_MAX, "step": 0.1},
            {"name": "measures", "value": {}, "required": False, "note": "직접 잰 치수 {measure_code: cm}, 비우면 추정"},
        ],
        "submit_label": "가입하기",
    }


# 목적: 기본값 fields 에 사용자가 넣은 값을 덮어 검사용 form dict 로 바꾸기
def fill_form(defaults, typed):
    form = {}
    for field in defaults["fields"]:
        form[field["name"]] = field["value"]
    for key in typed:
        form[key] = typed[key]
    return form


if __name__ == "__main__":
    defaults = signup_form_defaults(datetime.date.today())
    print("■ 가입 폼 기본값 (오늘 " + datetime.date.today().isoformat() + " 기준)")
    print(json.dumps(defaults, ensure_ascii=False, indent=2))

    empty_form = fill_form(defaults, {})
    print("\n■ 아무것도 안 넣고 제출하면 → 오류 " + str(len(validate(empty_form))) + "개")
    for error in validate(empty_form):
        print("  - " + error)

    typed = {"user_name": "예시사용자01", "email": "user01@example.com", "gender": "male",
             "birth_date": "1995-03-14", "height_cm": 172.2, "weight_kg": 62.5}
    print("\n■ 예시 회원 01 값으로 채우면 → 오류 " + str(len(validate(fill_form(defaults, typed)))) + "개")
