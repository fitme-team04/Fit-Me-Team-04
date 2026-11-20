# 목적: 회귀 기준선 — 성별마다 키(x)로 치수 하나(y, 기본 chest_girth)를 직선으로 예측하면 얼마나 맞나
# 누가 쓰나: AI
# 난이도: 고급 — 학습 표(_학습표.py) + 파이썬 회귀(최소제곱 직선·R²·MAE)
# 출력: 성별 키→chest_girth 회귀 표(n 5·slope·intercept, R² 남 0.267/여 0.004, MAE 5.88/13.72cm), 예측 2행
# y = 기울기 × x + 절편 (statistics.linear_regression, 최소제곱법)
# 실행: .venv/bin/python db/예시_코드/ai/3_고급/03_회귀_키로_치수_예측.py
# 주의: 예시 DB 는 성별마다 5명뿐이라 수치는 동작 확인용 (2명이면 직선이 두 점을 그대로 지나 R² = 1 이 되어 의미 없음).
#       ANSUR II / BodyM 전체를 적재하면 같은 코드로 제대로 된 기준선이 됨
import statistics
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import show
from _학습표 import load_rows                                       # 1명 = 1행 학습 표 (예시_코드/_학습표.py)


# 목적: 성별 하나의 (x, y) 짝 모으기. x 나 y 가 비면 뺌
def pairs(table, gender, x_col, y_col):
    xs = []
    ys = []
    for row in table:
        if row["gender"] != gender:
            continue
        if row[x_col] is None or row[y_col] is None:
            continue
        xs.append(row[x_col])
        ys.append(row[y_col])
    return xs, ys


# 목적: 직선 하나 학습 → {"slope", "intercept", "r2", "mae", "n"} (2명 미만이면 None)
def fit(xs, ys):
    if len(xs) < 2:
        return None
    if len(set(xs)) < 2:          # x 가 모두 같으면 직선을 못 그림
        return None
    model = statistics.linear_regression(xs, ys)
    slope = model.slope
    intercept = model.intercept

    # 학습 데이터 위에서의 오차 (평균 절대 오차 MAE) 와 결정계수 R²
    errors = []
    for i in range(len(xs)):
        predicted = slope * xs[i] + intercept
        errors.append(abs(ys[i] - predicted))
    mae = statistics.mean(errors)
    r2 = None
    if len(set(ys)) >= 2:
        r = statistics.correlation(xs, ys)
        r2 = r * r
    return {"slope": slope, "intercept": intercept, "r2": r2, "mae": mae, "n": len(xs)}


# 목적: 성별마다 학습 → 결과 표 행 목록 + {gender: model}
def train(table, x_col="height_cm", y_col="chest_girth"):
    rows = []
    models = {}
    for gender in ["male", "female"]:
        xs, ys = pairs(table, gender, x_col, y_col)
        model = fit(xs, ys)
        if model is None:
            rows.append({"gender": gender, "n": len(xs), "slope": "-", "intercept": "-", "r2": "-", "mae_cm": "-"})
            continue
        models[gender] = model
        r2_text = "-"
        if model["r2"] is not None:
            r2_text = round(model["r2"], 3)
        rows.append({"gender": gender, "n": model["n"], "slope": round(model["slope"], 3),
                     "intercept": round(model["intercept"], 2), "r2": r2_text,
                     "mae_cm": round(model["mae"], 2)})
    return rows, models


# 목적: 예측 하나
def predict(model, x):
    return model["slope"] * x + model["intercept"]


if __name__ == "__main__":
    table = load_rows()
    rows, models = train(table, "height_cm", "chest_girth")
    show("회귀 기준선: chest_girth ≈ slope × height_cm + intercept (학습 데이터 위 R²·MAE)", rows)

    examples = [("male", 175.0), ("female", 160.0)]
    result = []
    for gender, height in examples:
        if gender in models:
            result.append({"gender": gender, "height_cm": height,
                           "predicted_chest_girth": round(predict(models[gender], height), 1)})
        else:
            result.append({"gender": gender, "height_cm": height, "predicted_chest_girth": "-"})
    show("예측 예시", result)
    print()
    print("  ※ 예시 DB 는 성별마다 5명이라 수치는 동작 확인용 (2명이면 R² = 1, 두 점을 지나는 직선)")
