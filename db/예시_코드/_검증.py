# 목적: 화면에서 받은 사용자 신체 정보가 올바른지 검사하는 함수 모음 → 틀린 곳 목록 (DB 접속 없음). 예시가 아니라 import 하는 도우미
# 누가 쓰나: 아래 예시 (예시_코드/ 기준)
#   프론트: front/1_기본/01_성별_체형_선택값.py · 02_키_체중_범위_안내.py · 03_이메일_형식_확인.py · 04_BMI_체형_미리보기.py
#         · 05_가입폼_기본값.py · 06_입력값_검증.py
#         · 3_고급/01_회원정보_수정_롤백.py · 02_키_체중_수정_체형재계산.py · 03_치수_추가수정_롤백.py
#         · 05_사용자_신체정보_저장.py · 08_회원가입_요청_처리.py · 09_치수_저장_요청_처리.py · 10_추천_요청_처리.py
#   AI:   ai/1_기본/08_치수값_범위_점검.py
# 난이도: 기본 — SQL 없음, 파이썬 if 검사만
# 허용값은 db/테이블_정의서/공통.xlsx 표준 용어 시트 기준:
#   gender = male, female / 키·체중 = DECIMAL(5,1) (소수 1자리) / email 은 중복 불가(중복은 DB 가 막음)
#   body_type(선택) = underweight, normal, pre_obese, obese_1, obese_2, obese_3 (대한비만학회 BMI 단계, _body_type.py)
import datetime
import re

from _body_type import BODY_TYPES                             # 표준 용어: body_type 허용값

# 숫자 범위 (PoC 기준, 성인 의류 추천용으로 넉넉하게 잡음. 바꾸려면 여기만 고침)
#  - 키 120~230cm: ANSUR II·BodyM 성인 범위(약 140~200cm)보다 넓게
#  - 체중 30~250kg: 같은 이유로 넓게 (BodyM 에 100kg 넘는 사람 있음)
#  - 치수 10~250cm: 손목둘레(약 15cm)부터 엉덩이둘레(약 150cm)까지 넉넉하게
#  - 나이 14~100세: 생년월일로 계산
HEIGHT_MIN = 120.0
HEIGHT_MAX = 230.0
WEIGHT_MIN = 30.0
WEIGHT_MAX = 250.0
MEASURE_MIN = 10.0
MEASURE_MAX = 250.0
AGE_MIN = 14
AGE_MAX = 100

GENDERS = ("male", "female")                       # 표준 용어: gender 허용값
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$"  # 간단한 형식 검사 (실제 존재 여부는 확인 안 함)


# 목적: 값이 비었는지 (None 또는 공백 글자)
def is_empty(value):
    if value is None:
        return True
    if str(value).strip() == "":
        return True
    return False


# 목적: 숫자 하나 검사: 숫자인지, 범위 안인지, 소수 1자리 이하인지 → 틀린 곳 목록에 추가
def check_number(errors, name, value, low, high):
    if is_empty(value):
        errors.append(name + ": 값이 없음")
        return
    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append(name + ": 숫자가 아님 (" + str(value) + ")")
        return
    if number < low or number > high:
        errors.append(name + ": " + str(low) + " ~ " + str(high) + " 범위 밖 (" + str(value) + ")")
        return
    if round(number, 1) != number:
        errors.append(name + ": 소수 1자리까지만 (" + str(value) + ")")


# 목적: 생년월일 검사: YYYY-MM-DD 형식, 나이 범위
def check_birth_date(errors, value):
    if is_empty(value):
        errors.append("birth_date: 값이 없음")
        return
    try:
        born = datetime.date.fromisoformat(str(value))
    except ValueError:
        errors.append("birth_date: YYYY-MM-DD 형식이 아님 (" + str(value) + ")")
        return
    today = datetime.date.today()
    age = today.year - born.year
    if (today.month, today.day) < (born.month, born.day):
        age -= 1
    if age < AGE_MIN or age > AGE_MAX:
        errors.append("birth_date: 나이 " + str(AGE_MIN) + " ~ " + str(AGE_MAX) + "세 범위 밖 (" + str(age) + "세)")


# 목적: 입력 검사 본체 → 틀린 곳 목록 (빈 목록이면 통과)
# need_account=True 면 회원 정보(user_name·email·birth_date)도 검사 (가입·저장할 때)
def validate(form, need_account=True):
    errors = []

    gender = form.get("gender")
    if gender not in GENDERS:
        errors.append("gender: male / female 중 하나여야 함 (" + str(gender) + ")")
    check_number(errors, "height_cm", form.get("height_cm"), HEIGHT_MIN, HEIGHT_MAX)
    check_number(errors, "weight_kg", form.get("weight_kg"), WEIGHT_MIN, WEIGHT_MAX)

    # 선택: 체형. 보통은 저장할 때 키·체중으로 계산하므로 비워 두고, 값을 줬을 때만 허용값인지 검사
    body_type = form.get("body_type")
    if not is_empty(body_type) and body_type not in BODY_TYPES:
        errors.append("body_type: " + " / ".join(BODY_TYPES) + " 중 하나여야 함 (" + str(body_type) + ")")

    if need_account:
        user_name = form.get("user_name")
        if is_empty(user_name):
            errors.append("user_name: 값이 없음")
        elif len(str(user_name)) > 50:
            errors.append("user_name: 50자 이하")       # VARCHAR(50)
        email = form.get("email")
        if is_empty(email):
            errors.append("email: 값이 없음")
        elif len(str(email)) > 100 or re.match(EMAIL_PATTERN, str(email)) is None:
            errors.append("email: 형식이 맞지 않음 (" + str(email) + ")")
        check_birth_date(errors, form.get("birth_date"))

    # 선택: 직접 잰 치수 {measure_code: value_cm}. 코드 이름 형식만 검사 (실제 코드 목록은 DB 의 FK 가 막음)
    measures = form.get("measures")
    if measures is not None:
        for code in measures:
            if re.match(r"^[a-z][a-z0-9_]*$", str(code)) is None:
                errors.append("measures: 코드 형식이 아님 (" + str(code) + ")")
                continue
            check_number(errors, "measures." + str(code), measures[code], MEASURE_MIN, MEASURE_MAX)

    return errors
