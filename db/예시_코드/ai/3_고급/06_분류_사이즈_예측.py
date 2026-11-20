# 목적: 분류 기준선 — 규칙 추천 사이즈를 정답으로 놓고, 성별·키·체중만으로 새 사람의 사이즈를 맞히기
# 누가 쓰나: AI
# 난이도: 고급 — 규칙 추천(_추천.py)으로 정답 붙이기 + 파이썬 k-최근접 이웃 분류
# 출력: US 규칙 추천 정답 10명(M 2·없음 8), 남 178cm·여 158cm 각각 이웃 3명 표와 투표 결과(둘 다 없음)
#  1) 치수가 있는 사람마다 규칙 추천(_추천.py)으로 옷 한 벌의 사이즈 정답을 붙임
#  2) 새 사람은 성별·키·체중이 가까운 k 명의 정답을 다수결(k-최근접 이웃 투표)
# 실행: .venv/bin/python db/예시_코드/ai/3_고급/06_분류_사이즈_예측.py
# 주의: 예시 DB 는 옷 실측이 있는 사이즈가 지역마다 M 하나뿐이라 정답이 "M" / "없음" 두 가지만 나옴
import math
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show
from _추천 import recommend, body_from_profile                      # 규칙 추천 (예시_코드/_추천.py)
from _추정 import mean_and_sd                                       # 평균·표준편차 (예시_코드/_추정.py)

# 기본 옷: UNIQLO 크루넥T US (예시 DB 에서 옷 실측이 있는 사이즈: M)
DEFAULT_SOURCE = "uniqlo_site"
DEFAULT_ITEM = "E422992-000"
DEFAULT_REGION = "US"
NO_FIT = "없음"     # 모든 사이즈가 작을 때(규칙상 맞는 사이즈 없음)의 정답 이름


# 목적: 치수가 있는 사람 목록 (성별·키·체중 포함)
def measured_profiles():
    sql = """
        SELECT DISTINCT p.profile_id, p.gender, p.height_cm, p.weight_kg
        FROM body.profiles AS p
        JOIN body.measures AS m ON m.profile_id = p.profile_id
        WHERE p.height_cm IS NOT NULL
          AND p.weight_kg IS NOT NULL
          AND m.measure_method = 'measured'
        ORDER BY p.profile_id
    """
    return query(sql)


# 목적: 규칙 추천 1순위가 fit 이면 그 사이즈, 아니면 "없음"
def rule_label(body, source_name, item_code, region):
    table = recommend(body, source_name, item_code, region, verbose=False)
    if len(table) == 0 or table[0]["rank"] == "-":
        return None                    # 비교할 치수가 없음 → 학습에서 뺌
    if table[0]["size_status"] == "fit":
        return table[0]["size_label"]
    return NO_FIT


# 목적: 1) 정답 붙이기 → [{"profile_id", "gender", "height_cm", "weight_kg", "label"}]
def make_labels(source_name=DEFAULT_SOURCE, item_code=DEFAULT_ITEM, region=DEFAULT_REGION):
    labeled = []
    for p in measured_profiles():
        body = body_from_profile(p["profile_id"])
        label = rule_label(body, source_name, item_code, region)
        if label is None:
            continue
        labeled.append({"profile_id": p["profile_id"], "gender": p["gender"],
                        "height_cm": float(p["height_cm"]), "weight_kg": float(p["weight_kg"]),
                        "label": label})
    return labeled


# 목적: 정렬 기준 함수 (lambda 대신)
def by_distance(item):
    return item["distance"]


# 목적: 2) k-최근접 이웃 투표. 거리 = 표준화한 키·체중 차이 + 성별이 다르면 1 (성별을 0/1 특징으로 봄)
def predict(labeled, gender, height_cm, weight_kg, k=3):
    heights = []
    weights = []
    for row in labeled:
        heights.append(row["height_cm"])
        weights.append(row["weight_kg"])
    h_mean, h_sd = mean_and_sd(heights)
    w_mean, w_sd = mean_and_sd(weights)

    scored = []
    for row in labeled:
        dh = (height_cm - row["height_cm"]) / h_sd
        dw = (weight_kg - row["weight_kg"]) / w_sd
        dg = 0.0
        if row["gender"] != gender:
            dg = 1.0
        d = math.sqrt(dh * dh + dw * dw + dg * dg)
        scored.append({"profile_id": row["profile_id"], "gender": row["gender"],
                       "height_cm": row["height_cm"], "weight_kg": row["weight_kg"],
                       "label": row["label"], "distance": round(d, 3)})
    scored.sort(key=by_distance)
    if k > len(scored):
        k = len(scored)
    neighbors = scored[:k]

    # 다수결. 표가 같으면 더 가까운 이웃이 가진 정답 (neighbors 가 가까운 순이라 먼저 나온 쪽)
    votes = {}
    for nb in neighbors:
        if nb["label"] not in votes:
            votes[nb["label"]] = 0
        votes[nb["label"]] += 1
    best = None
    for nb in neighbors:
        if best is None or votes[nb["label"]] > votes[best]:
            best = nb["label"]
    return best, neighbors, votes


if __name__ == "__main__":
    labeled = make_labels()
    show("정답 붙이기: 규칙 추천 사이즈 (" + DEFAULT_SOURCE + " / " + DEFAULT_ITEM + " / " + DEFAULT_REGION + ")", labeled)

    examples = [("male", 178.0, 80.0), ("female", 158.0, 62.0)]
    for gender, height, weight in examples:
        label, neighbors, votes = predict(labeled, gender, height, weight, k=3)
        show("이웃 3명 (" + gender + ", " + str(height) + "cm, " + str(weight) + "kg)", neighbors)
        print("  투표:", votes, "→ 예측 사이즈:", label)
    print()
    print("  ※ 예시 DB 는 정답이 10명·2종류(M · 없음)뿐이라 동작 확인용. 실제 학습은 ANSUR II / BodyM 전체 적재 후")
