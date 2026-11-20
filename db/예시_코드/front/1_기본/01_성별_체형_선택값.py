# 목적: 가입·입력 화면의 성별·체형 드롭다운에 넣을 선택값(value·label) 만들기 + 받은 값이 허용값인지 확인 (DB 접속 없음)
# 누가 쓰나: 프론트
# 난이도: 기본 — SQL 없음, 도우미의 허용값 목록(_검증.GENDERS · _body_type.BODY_TYPES)을 화면용 모양으로 옮기기만
# 출력: 성별 드롭다운 2행·체형 드롭다운 7행(value·label·hint), 받은 값 허용 여부 표 7행(True/False)
# 실행: .venv/bin/python db/예시_코드/front/1_기본/01_성별_체형_선택값.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import show
from _검증 import GENDERS                              # 표준 용어: gender 허용값 (male, female)
from _body_type import BODY_TYPES, body_type_name      # 표준 용어: body_type 허용값 + 한글 이름

# 화면에 보여 줄 성별 한글 이름
GENDER_NAMES = {"male": "남성", "female": "여성"}

# 체형마다 BMI 구간 안내 글 (대한비만학회 2022 표 1, _body_type.py 주석과 같은 경계)
BMI_RANGE_TEXT = {
    "underweight": "BMI 18.5 미만",
    "normal": "BMI 18.5 ~ 22.9",
    "pre_obese": "BMI 23 ~ 24.9",
    "obese_1": "BMI 25 ~ 29.9",
    "obese_2": "BMI 30 ~ 34.9",
    "obese_3": "BMI 35 이상",
}


# 목적: 성별 드롭다운 선택값 목록 [{"value", "label"}]
def gender_options():
    options = []
    for gender in GENDERS:
        options.append({"value": gender, "label": GENDER_NAMES.get(gender, gender)})
    return options


# 목적: 체형 드롭다운 선택값 목록. 체형은 보통 키·체중으로 자동 계산하므로 맨 앞에 "자동 계산"(value 빈 글자)을 둠
def body_type_options():
    options = [{"value": "", "label": "자동 계산 (키·체중으로)", "hint": "저장할 때 BMI 로 정함"}]
    for body_type in BODY_TYPES:
        options.append({"value": body_type, "label": body_type_name(body_type), "hint": BMI_RANGE_TEXT[body_type]})
    return options


# 목적: 화면에서 받은 값이 드롭다운 선택값 중 하나인지 (주소창·API 로 직접 보낸 값 막기)
def is_allowed(value, options):
    for option in options:
        if option["value"] == value:
            return True
    return False


if __name__ == "__main__":
    genders = gender_options()
    body_types = body_type_options()
    show("성별 드롭다운", genders)
    show("체형 드롭다운", body_types)

    rows = []
    for value in ["male", "female", "man", ""]:
        rows.append({"field": "gender", "value": value, "allowed": is_allowed(value, genders)})
    for value in ["normal", "obese_2", "fat"]:
        rows.append({"field": "body_type", "value": value, "allowed": is_allowed(value, body_types)})
    show("받은 값 확인", rows)
