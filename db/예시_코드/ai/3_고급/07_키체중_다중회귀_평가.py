# 목적: 치수마다 다중 회귀(특징 = 키·체중·성별, 학습 표준화) 를 train 으로 학습 → test 에서 MAE·RMSE 로 평가하고 "평균값 찍기" 기준선과 비교
# 누가 쓰나: AI (치수 예측 모델의 평가 틀)
# 난이도: 고급 — CTE + 창 함수(ROW_NUMBER, 05 와 같은 나누기 규칙) + 3개 표 JOIN 피벗(MAX CASE) + 파이썬 표준화·정규방정식(가우스 소거)·MAE·RMSE
# 출력: test 12·18번, 치수 4개 회귀 vs 평균 test MAE·RMSE 표(chest MAE 2.33 vs 10.1), 계수 표, 예측 97.6cm
# 모델: y ≈ b0 + b1·z(키) + b2·z(체중) + b3·남성 (z = (값 − train 평균) / train 표준편차, test 에도 train 값으로 변환)
#       사람이 적어 계수가 튀지 않게 릿지(능선) 벌점 RIDGE 를 b1~b3 에 더함 (b0 는 벌점 없음)
# 실행: .venv/bin/python db/예시_코드/ai/3_고급/07_키체중_다중회귀_평가.py
# 주의: 예시 DB 는 test 가 2명뿐이라 수치는 동작 확인용. ANSUR II / BodyM 전체 적재 후 같은 코드로 의미 있는 평가가 됨
import math
import statistics
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show

TARGETS = ["chest_girth", "waist_girth", "hip_girth", "shoulder_width"]
RIDGE = 0.1


# 목적: 사람별 키·체중·성별·split + 예측 대상 치수 열 (05 와 같은 나누기 규칙)
def load_split_table(min_measures=3, test_every=3):
    sql = """
        WITH labeled AS (
            SELECT p.profile_id, p.gender
            FROM body.profiles AS p
            JOIN body.measures AS m ON m.profile_id = p.profile_id
            WHERE m.measure_method = 'measured'
              AND p.height_cm IS NOT NULL
              AND p.weight_kg IS NOT NULL
            GROUP BY p.profile_id
            HAVING COUNT(*) >= %s
        ),
        numbered AS (
            SELECT l.profile_id, l.gender,
                   ROW_NUMBER() OVER (PARTITION BY l.gender ORDER BY l.profile_id) AS rn
            FROM labeled AS l
        )
        SELECT n.profile_id, n.gender, p.height_cm, p.weight_kg,
               CASE WHEN MOD(n.rn, %s) = 0 THEN 'test' ELSE 'train' END AS split,
               MAX(CASE WHEN m.measure_code = 'chest_girth'    THEN m.value_cm END) AS chest_girth,
               MAX(CASE WHEN m.measure_code = 'waist_girth'    THEN m.value_cm END) AS waist_girth,
               MAX(CASE WHEN m.measure_code = 'hip_girth'      THEN m.value_cm END) AS hip_girth,
               MAX(CASE WHEN m.measure_code = 'shoulder_width' THEN m.value_cm END) AS shoulder_width
        FROM numbered AS n
        JOIN body.profiles AS p ON p.profile_id = n.profile_id
        JOIN body.measures AS m
          ON m.profile_id = n.profile_id
         AND m.measure_method = 'measured'
        GROUP BY n.profile_id, n.gender, n.rn, p.height_cm, p.weight_kg
        ORDER BY n.profile_id
    """
    table = []
    for row in query(sql, (min_measures, test_every)):
        item = {"profile_id": row["profile_id"], "gender": row["gender"], "split": row["split"],
                "height_cm": float(row["height_cm"]), "weight_kg": float(row["weight_kg"])}
        for code in TARGETS:
            item[code] = None
            if row[code] is not None:
                item[code] = float(row[code])
        table.append(item)
    return table


# 목적: train 행으로 표준화 기준(평균·표준편차) 구하기 (표준편차 0 이면 1)
def scaler(train_rows):
    params = {}
    for col in ["height_cm", "weight_kg"]:
        values = []
        for row in train_rows:
            values.append(row[col])
        sd = 1.0
        if len(values) >= 2:
            sd = statistics.stdev(values)
        if sd == 0:
            sd = 1.0
        params[col] = (statistics.mean(values), sd)
    return params


# 목적: 사람 한 명 → 특징 벡터 [1, z(키), z(체중), 남성 여부]
def features(row, params):
    zh = (row["height_cm"] - params["height_cm"][0]) / params["height_cm"][1]
    zw = (row["weight_kg"] - params["weight_kg"][0]) / params["weight_kg"][1]
    is_male = 0.0
    if row["gender"] == "male":
        is_male = 1.0
    return [1.0, zh, zw, is_male]


# 목적: 연립방정식 A·x = b 풀기 (가우스 소거 + 부분 피벗). 풀 수 없으면 None
def solve(a, b):
    n = len(b)
    m = []
    for i in range(n):
        m.append(list(a[i]) + [b[i]])
    for col in range(n):
        best = col
        for r in range(col + 1, n):
            if abs(m[r][col]) > abs(m[best][col]):
                best = r
        if abs(m[best][col]) < 1e-12:
            return None
        temp = m[col]                 # 가장 큰 값이 있는 줄을 위로 바꿔 놓기
        m[col] = m[best]
        m[best] = temp
        for r in range(n):
            if r == col:
                continue
            ratio = m[r][col] / m[col][col]
            for c in range(col, n + 1):
                m[r][c] -= ratio * m[col][c]
    x = []
    for i in range(n):
        x.append(m[i][n] / m[i][i])
    return x


# 목적: 릿지 회귀 학습: (XᵀX + λI)·w = Xᵀy (절편 칸은 λ 를 더하지 않음) → 계수 목록
def fit(xs, ys, ridge):
    size = len(xs[0])
    a = []
    b = []
    for i in range(size):
        a.append([0.0] * size)
        b.append(0.0)
    for k in range(len(xs)):
        for i in range(size):
            b[i] += xs[k][i] * ys[k]
            for j in range(size):
                a[i][j] += xs[k][i] * xs[k][j]
    for i in range(1, size):
        a[i][i] += ridge
    return solve(a, b)


# 목적: 예측 하나 = 계수 · 특징
def predict(weights, x):
    total = 0.0
    for i in range(len(x)):
        total += weights[i] * x[i]
    return total


# 목적: 오차 목록 → MAE(평균 절대 오차)·RMSE(평균 제곱 오차의 제곱근)
def mae_rmse(errors):
    abs_sum = 0.0
    sq_sum = 0.0
    for e in errors:
        abs_sum += abs(e)
        sq_sum += e * e
    return abs_sum / len(errors), math.sqrt(sq_sum / len(errors))


# 목적: 치수 하나 학습·평가 → 결과 한 행과 계수 (자료가 모자라면 계수 None)
def evaluate(table, target, ridge=RIDGE):
    train = []
    test = []
    for row in table:
        if row[target] is None:
            continue
        if row["split"] == "train":
            train.append(row)
        else:
            test.append(row)
    result = {"target": target, "n_train": len(train), "n_test": len(test)}
    if len(train) < 5 or len(test) == 0:
        result["note"] = "train 5명 미만 또는 test 없음 → 건너뜀"
        return result, None
    params = scaler(train)
    xs = []
    ys = []
    for row in train:
        xs.append(features(row, params))
        ys.append(row[target])
    weights = fit(xs, ys, ridge)
    if weights is None:
        result["note"] = "방정식을 풀 수 없음"
        return result, None
    train_mean = statistics.mean(ys)
    model_errors = []
    mean_errors = []
    for row in test:
        model_errors.append(predict(weights, features(row, params)) - row[target])
        mean_errors.append(train_mean - row[target])
    model_mae, model_rmse = mae_rmse(model_errors)
    base_mae, base_rmse = mae_rmse(mean_errors)
    result["mae_model"] = round(model_mae, 2)
    result["rmse_model"] = round(model_rmse, 2)
    result["mae_mean"] = round(base_mae, 2)
    result["rmse_mean"] = round(base_rmse, 2)
    better = "평균 기준선"
    if model_mae < base_mae:
        better = "회귀 모델"
    result["note"] = "더 나은 쪽: " + better
    return result, {"weights": weights, "params": params}


if __name__ == "__main__":
    table = load_split_table(3, 3)
    test_ids = []
    for row in table:
        if row["split"] == "test":
            test_ids.append(row["profile_id"])
    print("test profile_id:", test_ids, "/ 전체", len(table), "명")

    results = []
    models = {}
    for target in TARGETS:
        result, model = evaluate(table, target)
        results.append(result)
        if model is not None:
            models[target] = model
    show("치수별 다중 회귀 평가 (test MAE·RMSE, cm) vs 평균 기준선", results)

    if "chest_girth" in models:
        w = models["chest_girth"]["weights"]
        show("chest_girth 계수 (표준화 특징 기준)", [{"b0_intercept": round(w[0], 2), "b1_height_z": round(w[1], 2),
                                                  "b2_weight_z": round(w[2], 2), "b3_male": round(w[3], 2)}])
        example = {"gender": "male", "height_cm": 175.0, "weight_kg": 75.0}
        x = features(example, models["chest_girth"]["params"])
        print("  예측: 남성 175.0cm · 75.0kg → chest_girth ≈", round(predict(w, x), 1), "cm")
