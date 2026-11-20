# 목적: 한 명 빼기 교차검증(leave-one-out) 으로 k-NN 치수 추정(_추정.py)의 오차를 치수별 MAE·RMSE 로 재고, "같은 성별 평균" 기준선과 비교 + k 값 비교
# 누가 쓰나: AI (추정 모델 k 고르기·성능 보고)
# 난이도: 고급 — 2개 표 JOIN 조회(_추정.py) + 파이썬 교차검증 반복(사람마다 자기 빼고 이웃 찾기) + MAE·RMSE 집계
# 출력: k=3 한 명 빼기 22개 치수 k-NN·평균 MAE·RMSE 표(17개 k-NN 우세), k=1~4 합산 표, 최적 k=3(MAE 5.85)
# 실행: .venv/bin/python db/예시_코드/ai/3_고급/08_한명빼기_kNN_평가.py
# 주의: 예시 DB 는 성별마다 5명이라 수치는 동작 확인용
import math
import statistics
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import show
from _추정 import candidate_rows, group_by_profile, nearest      # k-NN 재료 (예시_코드/_추정.py)


# 목적: 한 사람(pid)을 뺀 나머지 사람 dict
def without(people, pid):
    others = {}
    for other in people:
        if other != pid:
            others[other] = people[other]
    return others


# 목적: 사람 묶음에서 치수 하나의 값 목록 (그 치수를 잰 사람만)
def values_of(people, code, ids):
    values = []
    for pid in ids:
        if code in people[pid]["measures"]:
            values.append(people[pid]["measures"][code])
    return values


# 목적: 성별 하나의 교차검증 → 오차 행 목록 [{"code", "knn_error", "mean_error"}]
def loo_errors(gender, k):
    people = group_by_profile(candidate_rows(gender))
    errors = []
    for pid in people:
        others = without(people, pid)
        if len(others) == 0:
            continue
        neighbors = nearest(others, people[pid]["height"], people[pid]["weight"], k)
        neighbor_ids = []
        for nb in neighbors:
            neighbor_ids.append(nb["profile_id"])
        for code in people[pid]["measures"]:
            if code == "height":
                continue
            actual = people[pid]["measures"][code]
            knn_values = values_of(others, code, neighbor_ids)
            all_values = values_of(others, code, list(others.keys()))
            if len(knn_values) == 0 or len(all_values) == 0:
                continue
            errors.append({"code": code, "knn_error": statistics.mean(knn_values) - actual,
                           "mean_error": statistics.mean(all_values) - actual})
    return errors


# 목적: 오차 목록 → (MAE, RMSE)
def mae_rmse(values):
    abs_sum = 0.0
    sq_sum = 0.0
    for v in values:
        abs_sum += abs(v)
        sq_sum += v * v
    return abs_sum / len(values), math.sqrt(sq_sum / len(values))


# 목적: 치수별 요약 표 (평가 횟수 min_n 이상인 치수만)
def per_measure(errors, min_n=3):
    by_code = {}
    for e in errors:
        if e["code"] not in by_code:
            by_code[e["code"]] = {"knn": [], "mean": []}
        by_code[e["code"]]["knn"].append(e["knn_error"])
        by_code[e["code"]]["mean"].append(e["mean_error"])
    result = []
    for code in sorted(by_code):
        knn = by_code[code]["knn"]
        if len(knn) < min_n:
            continue
        knn_mae, knn_rmse = mae_rmse(knn)
        mean_mae, mean_rmse = mae_rmse(by_code[code]["mean"])
        winner = "평균"
        if knn_mae < mean_mae:
            winner = "k-NN"
        result.append({"measure_code": code, "n": len(knn), "knn_mae": round(knn_mae, 2),
                       "knn_rmse": round(knn_rmse, 2), "mean_mae": round(mean_mae, 2),
                       "mean_rmse": round(mean_rmse, 2), "better": winner})
    return result


# 목적: 두 성별 오차를 합침
def both_genders(k):
    errors = []
    for gender in ["male", "female"]:
        errors.extend(loo_errors(gender, k))
    return errors


if __name__ == "__main__":
    errors = both_genders(3)
    show("한 명 빼기 평가 k = 3 (치수별, cm)", per_measure(errors, 3))

    rows = []
    for k in [1, 2, 3, 4]:
        errs = both_genders(k)
        knn_list = []
        mean_list = []
        for e in errs:
            knn_list.append(e["knn_error"])
            mean_list.append(e["mean_error"])
        knn_mae, knn_rmse = mae_rmse(knn_list)
        mean_mae, mean_rmse = mae_rmse(mean_list)
        rows.append({"k": k, "evaluations": len(errs), "knn_mae": round(knn_mae, 2), "knn_rmse": round(knn_rmse, 2),
                     "mean_mae": round(mean_mae, 2)})
    show("k 값 비교 (모든 치수 합산)", rows)
    best = rows[0]
    for row in rows:
        if row["knn_mae"] < best["knn_mae"]:
            best = row
    print("  → MAE 가 가장 작은 k:", best["k"])
