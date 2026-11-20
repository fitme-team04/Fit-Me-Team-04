# 목적: 키·체중을 입력하는 동안 화면에 BMI·체형을 미리 보여 주기 (저장 전 계산, DB 접속 없음)
# 누가 쓰나: 프론트
# 난이도: 기본 — SQL 없음, _body_type.py 계산 함수(bmi_of · body_type_of) 호출과 결과 글 만들기만
# 출력: 키·체중 7쌍의 BMI·body_type·한글 label·message 표(마지막 'abc' 행은 계산 안 함)
# 실행: .venv/bin/python db/예시_코드/front/1_기본/04_BMI_체형_미리보기.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import show
from _body_type import bmi_of, body_type_of, body_type_name   # 키·체중 → BMI → 체형 (대한비만학회 기준)
from _검증 import HEIGHT_MIN, HEIGHT_MAX, WEIGHT_MIN, WEIGHT_MAX, check_number


# 목적: 미리보기 한 줄 {height_cm, weight_kg, bmi, body_type, label, message}. 입력이 틀리면 계산 대신 이유를 보여 줌
def preview(height_cm, weight_kg):
    errors = []
    check_number(errors, "height_cm", height_cm, HEIGHT_MIN, HEIGHT_MAX)
    check_number(errors, "weight_kg", weight_kg, WEIGHT_MIN, WEIGHT_MAX)
    result = {"height_cm": height_cm, "weight_kg": weight_kg, "bmi": "-", "body_type": "-", "label": "-", "message": ""}
    if len(errors) > 0:
        result["message"] = "계산 안 함: " + errors[0]
        return result

    bmi = bmi_of(height_cm, weight_kg)
    body_type = body_type_of(height_cm, weight_kg)
    result["bmi"] = round(bmi, 1)
    result["body_type"] = body_type
    result["label"] = body_type_name(body_type)
    result["message"] = "BMI " + str(round(bmi, 1)) + " → " + body_type_name(body_type)
    return result


if __name__ == "__main__":
    rows = []
    # 예시 회원 5명(db/sample/sample_data.sql profile 18~22)의 키·체중 + 경계값 + 틀린 입력
    samples = [(172.2, 62.5), (171.2, 79.1), (176.9, 75.6), (171.3, 52.0), (185.3, 109.4),
               (170.0, 66.5), ("abc", 70)]
    for height_cm, weight_kg in samples:
        rows.append(preview(height_cm, weight_kg))
    show("BMI·체형 미리보기", rows)
