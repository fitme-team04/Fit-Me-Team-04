# 목적: 키·체중 입력칸의 범위 규칙(최소·최대·소수 자리) 안내 글을 만들고, 칸 하나씩 바로 검사해 메시지 보여 주기 (DB 접속 없음)
# 누가 쓰나: 프론트
# 난이도: 기본 — SQL 없음, _검증.py 의 숫자 범위 상수와 check_number 를 칸 하나에 쓰기만
# 출력: 키·체중 입력칸 규칙 표 2행(min·max·step·help), 칸별 검사 8행(OK 또는 범위 밖·소수·숫자 아님 메시지)
# 실행: .venv/bin/python db/예시_코드/front/1_기본/02_키_체중_범위_안내.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import show
from _검증 import HEIGHT_MIN, HEIGHT_MAX, WEIGHT_MIN, WEIGHT_MAX, check_number   # 범위 숫자는 _검증.py 맨 위


# 목적: 입력칸 규칙 목록 (HTML <input type="number" min max step> 과 안내 글에 그대로 씀)
def range_rules():
    rules = [
        {"field": "height_cm", "label": "키", "unit": "cm", "min": HEIGHT_MIN, "max": HEIGHT_MAX, "step": 0.1},
        {"field": "weight_kg", "label": "체중", "unit": "kg", "min": WEIGHT_MIN, "max": WEIGHT_MAX, "step": 0.1},
    ]
    for rule in rules:
        rule["help"] = (rule["label"] + " " + str(rule["min"]) + " ~ " + str(rule["max"]) + rule["unit"]
                        + ", 소수 1자리까지 입력")
    return rules


# 목적: 규칙 목록에서 칸 이름(field)으로 규칙 하나 찾기 (없으면 None)
def rule_of(field):
    for rule in range_rules():
        if rule["field"] == field:
            return rule
    return None


# 목적: 칸 하나만 검사 → 화면 아래에 띄울 메시지 (통과면 "OK")
def check_field(field, value):
    rule = rule_of(field)
    if rule is None:
        return "알 수 없는 칸: " + str(field)
    errors = []
    check_number(errors, field, value, rule["min"], rule["max"])
    if len(errors) == 0:
        return "OK"
    return errors[0]


if __name__ == "__main__":
    show("키·체중 입력칸 규칙", range_rules())

    rows = []
    samples = [("height_cm", "172.2"), ("height_cm", 120), ("height_cm", 230.1), ("height_cm", "175.25"),
               ("height_cm", "abc"), ("weight_kg", 62.5), ("weight_kg", ""), ("weight_kg", 29.9)]
    for field, value in samples:
        rows.append({"field": field, "value": value, "message": check_field(field, value)})
    show("칸별 바로 검사", rows)
