# 목적: 치수 추정 함수 모음 — 성별·키·체중 → 비슷한 실측자 k 명(k-최근접 이웃)의 치수 평균. 예시가 아니라 import 하는 도우미
# 누가 쓰나: 아래 예시 (예시_코드/ 기준)
#   AI:   ai/3_고급/02_최근접이웃_치수_추정.py · 06_분류_사이즈_예측.py · 08_한명빼기_kNN_평가.py
#         · 09_더미회원_추정_실측_비교.py · 10_규칙추천_실측vs추정_교차검사.py
#   프론트: front/3_고급/05_사용자_신체정보_저장.py · 10_추천_요청_처리.py
# 난이도: 고급 — 2개 표 JOIN 조회 + 파이썬 k-최근접 이웃(표준화 거리) 계산
# 주의: 예시 DB 에는 치수를 잰 사람이 몇 명뿐이라 결과는 거친 기준선임.
#       ANSUR II / BodyM 전체를 적재하면 같은 코드로 더 정확해짐
import math
import statistics

from _db import query, show

# 추정값을 body.measures 에 저장할 때 model_version 에 넣는 이름
MODEL_VERSION = "knn_baseline_v1"


# 목적: 이웃 후보: 같은 성별 + 키·체중이 있고 + 실측(measured) 치수가 있는 사람들의 치수 행
def candidate_rows(gender):
    sql = """
        SELECT p.profile_id, p.height_cm, p.weight_kg,
               m.measure_code, m.value_cm
        FROM body.profiles AS p
        JOIN body.measures AS m ON m.profile_id = p.profile_id
        WHERE p.gender = %s
          AND p.height_cm IS NOT NULL
          AND p.weight_kg IS NOT NULL
          AND m.measure_method = 'measured'
        ORDER BY p.profile_id, m.measure_code
    """
    return query(sql, (gender,))


# 목적: 치수 행 목록 → 사람별로 묶기 {profile_id: {"height": 키, "weight": 체중, "measures": {코드: 값}}}
def group_by_profile(rows):
    people = {}
    for row in rows:
        pid = row["profile_id"]
        if pid not in people:
            people[pid] = {
                "height": float(row["height_cm"]),
                "weight": float(row["weight_kg"]),
                "measures": {},
            }
        people[pid]["measures"][row["measure_code"]] = float(row["value_cm"])
    return people


# 목적: 평균·표준편차 (사람이 1명이거나 모두 같은 값이면 표준편차 1 로 둠 → 0 으로 나누기 방지)
def mean_and_sd(values):
    mean = statistics.mean(values)
    sd = 1.0
    if len(values) >= 2:
        sd = statistics.stdev(values)
    if sd == 0:
        sd = 1.0
    return mean, sd


# 목적: 표준화 거리: 키·체중을 각각 (값 − 평균) / 표준편차 로 바꾼 뒤 직선 거리
def distance(h1, w1, h2, w2, h_sd, w_sd):
    dh = (h1 - h2) / h_sd
    dw = (w1 - w2) / w_sd
    return math.sqrt(dh * dh + dw * dw)


# 목적: 정렬 기준 함수 (lambda 대신)
def by_distance(item):
    return item["distance"]


# 목적: 가장 가까운 사람 k 명 → [{"profile_id", "height_cm", "weight_kg", "distance"}, ...]
def nearest(people, height_cm, weight_kg, k):
    heights = []
    weights = []
    for pid in people:
        heights.append(people[pid]["height"])
        weights.append(people[pid]["weight"])
    h_mean, h_sd = mean_and_sd(heights)
    w_mean, w_sd = mean_and_sd(weights)

    scored = []
    for pid in people:
        d = distance(height_cm, weight_kg, people[pid]["height"], people[pid]["weight"], h_sd, w_sd)
        scored.append({
            "profile_id": pid,
            "height_cm": people[pid]["height"],
            "weight_kg": people[pid]["weight"],
            "distance": round(d, 3),
        })
    scored.sort(key=by_distance)

    if k > len(scored):          # k 는 후보 수를 넘지 않음
        k = len(scored)
    return scored[:k]


# 목적: 치수 코드 → 한글 이름
def korean_names():
    rows = query("SELECT measure_code, korean_name FROM ref.measure_definitions")
    names = {}
    for row in rows:
        names[row["measure_code"]] = row["korean_name"]
    return names


# 목적: 추정 본체: 이웃들의 치수 코드별 평균 → [{"measure_code", "korean_name", "value_cm", "neighbor_tally"}, ...]
# 키(height)는 입력값이 있으므로 추정하지 않음
def estimate(gender, height_cm, weight_kg, k=5, verbose=False):
    people = group_by_profile(candidate_rows(gender))
    if len(people) == 0:
        print("  (" + gender + " 성별로 치수를 잰 사람이 없어 추정할 수 없음)")
        return []

    neighbors = nearest(people, float(height_cm), float(weight_kg), k)
    if verbose:
        show("이웃 (" + gender + ", 키 " + str(height_cm) + " · 체중 " + str(weight_kg) + ", k = " + str(len(neighbors)) + ")", neighbors)

    # 치수 코드별로 이웃 값 모으기 (그 치수를 잰 이웃만)
    values_by_code = {}
    for nb in neighbors:
        measures = people[nb["profile_id"]]["measures"]
        for code in measures:
            if code == "height":
                continue
            if code not in values_by_code:
                values_by_code[code] = []
            values_by_code[code].append(measures[code])

    names = korean_names()
    result = []
    for code in sorted(values_by_code):
        values = values_by_code[code]
        result.append({
            "measure_code": code,
            "korean_name": names.get(code, ""),
            "value_cm": round(statistics.mean(values), 1),
            "neighbor_tally": len(values),
        })
    return result


# 목적: 결과 목록 → {measure_code: value_cm} (_추천.py recommend 입력 모양)
def to_body(result):
    body = {}
    for row in result:
        body[row["measure_code"]] = row["value_cm"]
    return body


# 목적: 기준선 안내 문구
def print_note():
    print()
    print("  ※ 기준선 추정: 예시 DB 에는 치수를 잰 사람이 몇 명뿐이라 오차가 큼.")
    print("    ANSUR II / BodyM 전체를 적재하면 같은 코드로 더 정확해짐.")
