# 목적: 키·체중 → BMI → 체형(body_type) 계산 공통 도우미 (예시가 아니라 front·3d 예시가 import 하는 파일, DB 접속 없음)
# 누가 쓰나: 도우미 _검증.py 와 아래 예시 (예시_코드/ 기준)
#   공통: 공통/사람/1_기본/07_체형_골라_신체정보.py · 2_심화/04_체형별_BMI_범위.py · 05_사용자_신체정보_목록.py
#         · 3_고급/06_체형별_평균치수.py · 08_허리키비율_체형비교.py · 10_회원_최신_요약카드.py
#   3D:   3d/3_고급/01_조건별_사람_찾기.py
#   AI:   ai/1_기본/07_체형_라벨_분포.py · 09_체형라벨_재계산_검사.py · 10_키체중_기초통계.py · 2_심화/05_학습가능_체형별_인원.py
#   프론트: front/1_기본/01_성별_체형_선택값.py · 04_BMI_체형_미리보기.py
#         · 3_고급/02_키_체중_수정_체형재계산.py · 05_사용자_신체정보_저장.py · 07_마이페이지_응답_JSON.py · 08_회원가입_요청_처리.py
# 난이도: 기본 — SQL 없음, 파이썬 계산만
# 기준: 대한비만학회(KSSO) 비만 진료지침 2022 8판 요약본 표 1 "한국인에서 체질량지수와 허리둘레에 따른 비만 동반 질환 위험도"
#   https://general.kosso.or.kr/html/user/core/view/reaction/main/kosso/inc/data/guideline2022_vol8.pdf
#   저체중 < 18.5 / 정상 18.5~22.9 / 비만전단계 23~24.9 / 1단계 비만 25~29.9 / 2단계 비만 30~34.9 / 3단계 비만 ≥ 35 (kg/m²)
# DB 의 body.profiles.body_type 허용값(CHECK chk_profiles_body_type, db/sql/24_body_profiles_body_type.sql)과 같은 값

KSSO_URL = "https://general.kosso.or.kr/html/user/core/view/reaction/main/kosso/inc/data/guideline2022_vol8.pdf"

# 허용값 (작은 BMI 부터). 표준 용어: db/테이블_정의서/공통.xlsx 표준 용어 시트 body_type
BODY_TYPES = ("underweight", "normal", "pre_obese", "obese_1", "obese_2", "obese_3")

# 화면에 보여 줄 한글 이름 (KSSO 표 1 의 분류 이름)
BODY_TYPE_NAMES = {
    "underweight": "저체중",
    "normal": "정상",
    "pre_obese": "비만 전단계",
    "obese_1": "1단계 비만",
    "obese_2": "2단계 비만",
    "obese_3": "3단계 비만",
}


# 목적: BMI = 체중 kg / (키 m)². 키·체중 중 하나라도 없으면 None
def bmi_of(height_cm, weight_kg):
    if height_cm is None or weight_kg is None:
        return None
    height_m = float(height_cm) / 100
    if height_m <= 0:
        return None
    return float(weight_kg) / (height_m * height_m)


# 목적: 키·체중 → body_type 값 하나 (계산 못 하면 None = DB 에 NULL)
# 경계는 KSSO 표 그대로: 23 은 비만 전단계, 25 는 1단계 비만 (이상은 포함, 미만은 아래 단계)
def body_type_of(height_cm, weight_kg):
    bmi = bmi_of(height_cm, weight_kg)
    if bmi is None:
        return None
    if bmi < 18.5:
        return "underweight"
    if bmi < 23:
        return "normal"
    if bmi < 25:
        return "pre_obese"
    if bmi < 30:
        return "obese_1"
    if bmi < 35:
        return "obese_2"
    return "obese_3"


# 목적: body_type 값 → 한글 이름 (None 이면 "-")
def body_type_name(body_type):
    if body_type is None:
        return "-"
    return BODY_TYPE_NAMES.get(body_type, body_type)
