# 목적: 규칙 기반 사이즈 추천 함수 모음 — 내 신체 치수 ↔ 옷 사이즈별 치수 비교 (db/query/recommend/01~03 과 같은 규칙). 예시가 아니라 import 하는 도우미
# 누가 쓰나: 아래 예시 (예시_코드/ 기준)
#   AI:   ai/3_고급/01_규칙_사이즈_추천.py · 06_분류_사이즈_예측.py · 10_규칙추천_실측vs추정_교차검사.py
#   프론트: front/3_고급/10_추천_요청_처리.py
# 난이도: 고급 — 3개 표 LEFT JOIN 조회 + 파이썬으로 여유분 계산·순위 매기기
# 규칙 (AI 파트의 비교 기준 baseline: 모델 결과를 이 규칙 추천과 비교함)
#  - 여유분(ease) = 옷 치수 × factor − 신체 치수 (ref.measure_maps, 옷 실측 basis = garment)
#  - 모든 항목 여유분 ≥ 0 이면 fit, 하나라도 음수면 small
#  - 순위: fit 먼저, 그 안에서 평균 여유분이 작은 순 (02_size_rank.sql)
#  - 권장 체형 범위(basis = body): low ≤ 신체 ≤ high 인 항목 수 / 비교 항목 수 (03_body_range_fit.sql, 참고용)
from decimal import Decimal, ROUND_HALF_UP

from _db import query, show


# 목적: 숫자 → Decimal (float 오차 없이 SQL 의 DECIMAL 계산과 같게 하려고 글자로 바꿔서 만듦)
def to_dec(value):
    return Decimal(str(value))


# 목적: 소수 첫째 자리 반올림. MySQL ROUND 처럼 .5 는 올림 (파이썬 round 는 6.25 → 6.2 라 결과가 달라짐)
def round1(value):
    return float(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


# 목적: 한 사람(profile_id)의 신체 치수 → {measure_code: value_cm}
def body_from_profile(profile_id):
    sql = """
        SELECT m.measure_code, m.value_cm
        FROM body.measures AS m
        WHERE m.profile_id = %s
        ORDER BY m.measure_code
    """
    body = {}
    for row in query(sql, (profile_id,)):
        body[row["measure_code"]] = float(row["value_cm"])
    return body


# 목적: 신체 ↔ 옷 대응 규칙 목록 (ref.measure_maps)
def measure_maps():
    sql = """
        SELECT mm.body_measure_code, mm.garment_measure_code, mm.factor
        FROM ref.measure_maps AS mm
        ORDER BY mm.body_measure_code
    """
    return query(sql)


# 목적: 옷 하나(출처 + 상품번호)·지역의 사이즈별 치수. 치수가 없는 사이즈도 보이도록 LEFT JOIN
def size_rows(source_name, item_code, region):
    sql = """
        SELECT s.size_id, s.size_label, s.region,
               gm.basis, gm.measure_code, gm.value_cm, gm.low_cm, gm.high_cm
        FROM garment.sizes AS s
        JOIN garment.garments AS g ON g.garment_id = s.garment_id
        LEFT JOIN garment.measures AS gm ON gm.size_id = s.size_id
        WHERE g.source_name = %s
          AND g.item_code = %s
          AND s.region = %s
        ORDER BY s.size_id, gm.basis, gm.measure_code
    """
    return query(sql, (source_name, item_code, region))


# 목적: 사이즈 행 목록 → 사이즈별로 묶기 [{"size_id", "size_label", "region", "garment": {코드: 값}, "body": {코드: (low, high)}}]
def group_by_size(rows):
    sizes = []
    by_id = {}
    for row in rows:
        sid = row["size_id"]
        if sid not in by_id:
            item = {"size_id": sid, "size_label": row["size_label"], "region": row["region"],
                    "garment": {}, "body": {}}
            by_id[sid] = item
            sizes.append(item)
        if row["basis"] == "garment" and row["value_cm"] is not None:
            by_id[sid]["garment"][row["measure_code"]] = to_dec(row["value_cm"])
        if row["basis"] == "body":
            by_id[sid]["body"][row["measure_code"]] = (row["low_cm"], row["high_cm"])
    return sizes


# 목적: 사이즈 하나의 여유분 {신체 코드: 여유분}. 옷 치수와 내 치수가 둘 다 있는 대응만 계산
def ease_for_size(size, body, maps):
    eases = {}
    for mm in maps:
        g_code = mm["garment_measure_code"]
        b_code = mm["body_measure_code"]
        if g_code in size["garment"] and b_code in body:
            eases[b_code] = size["garment"][g_code] * to_dec(mm["factor"]) - to_dec(body[b_code])
    return eases


# 목적: 사이즈 하나의 권장 범위 검사 → (범위 안 항목 수, 비교 항목 수)
# SQL BETWEEN 처럼 low·high 중 하나라도 NULL 이면 "범위 안"으로 세지 않음
def range_check(size, body):
    in_range = 0
    compared = 0
    for code in size["body"]:
        if code not in body:
            continue
        compared += 1
        low = size["body"][code][0]
        high = size["body"][code][1]
        if low is None or high is None:
            continue
        value = to_dec(body[code])
        if to_dec(low) <= value and value <= to_dec(high):
            in_range += 1
    return in_range, compared


# 목적: 순위 정렬 기준: (small 이면 뒤로, 평균 여유분 작은 순) — 02_size_rank.sql 의 ORDER BY 와 같음
def rank_key(item):
    is_small = 0
    if item["min_ease"] < 0:
        is_small = 1
    return (is_small, item["avg_ease"])


# 목적: 추천 본체 → 순위 순서의 표 행 목록 (비교할 치수가 없는 사이즈는 빼고, 이름만 따로 출력)
def recommend(body, source_name, item_code, region, verbose=True):
    maps = measure_maps()
    sizes = group_by_size(size_rows(source_name, item_code, region))

    # 표에 쓸 여유분 열 (대응 규칙 순서, 실제로 계산된 것만)
    ease_codes = []
    scored = []
    skipped = []
    for size in sizes:
        eases = ease_for_size(size, body, maps)
        in_range, compared = range_check(size, body)
        if len(eases) == 0 and compared == 0:
            skipped.append(size["size_label"])
            continue
        for code in eases:
            if code not in ease_codes:
                ease_codes.append(code)
        item = {"size": size, "eases": eases, "in_range": in_range, "compared": compared,
                "min_ease": None, "avg_ease": None}
        if len(eases) > 0:
            values = list(eases.values())
            item["min_ease"] = min(values)
            item["avg_ease"] = sum(values) / len(values)
        scored.append(item)

    # 여유분이 있는 사이즈만 순위를 매김 (SQL 02 는 여유분 행이 있는 사이즈만 나옴)
    ranked = []
    unranked = []
    for item in scored:
        if item["avg_ease"] is None:
            unranked.append(item)
        else:
            ranked.append(item)
    ranked.sort(key=rank_key)

    table = []
    rank = 0
    for item in ranked + unranked:
        row = {"size_label": item["size"]["size_label"]}
        for code in ease_codes:
            if code in item["eases"]:
                row["여유:" + code] = round1(item["eases"][code])
            else:
                row["여유:" + code] = "-"
        if item["avg_ease"] is None:
            row["avg_ease"] = "-"
            row["size_status"] = "-"
            row["rank"] = "-"
        else:
            rank += 1
            row["avg_ease"] = round1(item["avg_ease"])
            if item["min_ease"] >= 0:
                row["size_status"] = "fit"
            else:
                row["size_status"] = "small"
            row["rank"] = rank
        if item["compared"] == 0:
            row["권장범위"] = "-"
        else:
            row["권장범위"] = str(item["in_range"]) + "/" + str(item["compared"])
        table.append(row)

    if verbose:
        print_result(table, skipped, body, maps, source_name, item_code, region)
    return table


# 목적: 추천 결과 출력: 표 + 추천 한 줄 + 비교 못 한 것 안내
def print_result(table, skipped, body, maps, source_name, item_code, region):
    show("사이즈 추천 (" + source_name + " / " + item_code + " / " + region + ")", table)
    if len(table) == 0 or table[0]["rank"] == "-":
        print("  → 비교할 수 있는 치수가 없음")
    elif table[0]["size_status"] == "fit":
        print("  → 추천 사이즈: " + str(table[0]["size_label"]) + " (모든 항목 여유분 ≥ 0 중 평균 여유분이 가장 작음)")
    else:
        print("  → 맞는 사이즈 없음 (모두 small). 가장 가까운 사이즈: " + str(table[0]["size_label"]))
    if len(skipped) > 0:
        print("  · 치수 자료가 없어 뺀 사이즈: " + ", ".join(skipped))
    missing = []
    for mm in maps:
        if mm["body_measure_code"] not in body:
            missing.append(mm["body_measure_code"])
    if len(missing) > 0:
        print("  · 내 치수에 없어 비교 못 하는 항목: " + ", ".join(missing))
