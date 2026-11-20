# 목적: 규칙 추천(_추천.py)에 실측 치수를 넣은 사이즈 vs k-NN 추정 치수(본인 제외)를 넣은 사이즈를 사람마다 비교 → 일치율·혼동표(confusion count)
# 누가 쓰나: AI (키·체중만 받은 추정값으로 추천해도 실측 기준 추천과 같은 사이즈가 나오는지 = 모델 ↔ 규칙 교차 검사)
# 난이도: 고급 — 4개 표(brands·garments·sizes·garment.measures) JOIN GROUP BY 로 비교 가능 사이즈 확인 + 규칙 추천 + 파이썬 k-NN 한 명 빼기 + 혼동표 집계
# 출력: 비교 가능 사이즈 KR·US M, 10명 실측 vs 추정 치수 규칙 추천 표·혼동표, 일치율 KR 90%·US 80%
# 실행: .venv/bin/python db/예시_코드/ai/3_고급/10_규칙추천_실측vs추정_교차검사.py
# 06 은 규칙 사이즈를 정답으로 키·체중 투표 분류, 여기는 "추정 치수 → 같은 규칙" 경로가 실측 경로와 같은 답을 내는지
import statistics
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show
from _추천 import recommend, body_from_profile                  # 규칙 추천 (예시_코드/_추천.py)
from _추정 import candidate_rows, group_by_profile, nearest      # k-NN 재료 (예시_코드/_추정.py)

SOURCE = "uniqlo_site"
ITEM = "E422992-000"
NO_FIT = "없음"           # 규칙상 모든 사이즈가 small
NO_COMPARE = "비교불가"   # 비교할 치수가 없음


# 목적: 옷 한 벌의 지역·사이즈별 옷 실측 치수 수 (브랜드 이름 포함, 치수가 있는 사이즈만)
def comparable_sizes(source_name, item_code):
    sql = """
        SELECT b.brand_name, g.item_code, s.region, s.size_label,
               COUNT(*) AS garment_measure_tally,
               GROUP_CONCAT(gm.measure_code ORDER BY gm.measure_code) AS codes
        FROM garment.brands AS b
        JOIN garment.garments AS g ON g.brand_id = b.brand_id
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        JOIN garment.measures AS gm ON gm.size_id = s.size_id
        WHERE g.source_name = %s
          AND g.item_code = %s
          AND gm.basis = 'garment'
        GROUP BY b.brand_name, g.item_code, s.region, s.size_label
        ORDER BY s.region, s.size_label
    """
    return query(sql, (source_name, item_code))


# 목적: 규칙 추천 1순위 → 사이즈 이름 / "없음" / "비교불가"
def rule_label(body, region):
    table = recommend(body, SOURCE, ITEM, region, verbose=False)
    if len(table) == 0 or table[0]["rank"] == "-":
        return NO_COMPARE
    if table[0]["size_status"] == "fit":
        return table[0]["size_label"]
    return NO_FIT


# 목적: 한 사람을 뺀 같은 성별 실측자로 k-NN 추정 치수 {코드: 값}
def loo_estimate(people, pid, k):
    others = {}
    for other in people:
        if other != pid:
            others[other] = people[other]
    neighbors = nearest(others, people[pid]["height"], people[pid]["weight"], k)
    values_by_code = {}
    for nb in neighbors:
        measures = others[nb["profile_id"]]["measures"]
        for code in measures:
            if code not in values_by_code:
                values_by_code[code] = []
            values_by_code[code].append(measures[code])
    body = {}
    for code in values_by_code:
        body[code] = round(statistics.mean(values_by_code[code]), 1)
    return body


# 목적: 사람마다 실측 경로·추정 경로 사이즈 (지역 하나)
def cross_check(region, k=3):
    result = []
    for gender in ["male", "female"]:
        people = group_by_profile(candidate_rows(gender))
        for pid in sorted(people):
            actual_label = rule_label(body_from_profile(pid), region)
            estimated_label = rule_label(loo_estimate(people, pid, k), region)
            result.append({"profile_id": pid, "gender": gender, "region": region,
                           "rule_on_measured": actual_label, "rule_on_estimated": estimated_label,
                           "same": actual_label == estimated_label})
    return result


# 목적: 혼동표: 행 = 실측 경로 사이즈, 열 = 추정 경로 사이즈, 칸 = 사람 수
def confusion(rows):
    labels = []
    for row in rows:
        for key in ["rule_on_measured", "rule_on_estimated"]:
            if row[key] not in labels:
                labels.append(row[key])
    labels.sort()
    table = []
    for actual in labels:
        line = {"실측_경로": actual}
        for predicted in labels:
            tally = 0
            for row in rows:
                if row["rule_on_measured"] == actual and row["rule_on_estimated"] == predicted:
                    tally += 1
            line["추정=" + predicted] = tally
        table.append(line)
    return table


if __name__ == "__main__":
    show("비교 가능한 사이즈 (" + SOURCE + " / " + ITEM + ")", comparable_sizes(SOURCE, ITEM))
    for region in ["KR", "US"]:
        rows = cross_check(region, 3)
        show("사람별 규칙 추천: 실측 치수 vs 추정 치수 (" + region + ", k = 3)", rows)
        show("혼동표 (" + region + ")", confusion(rows))
        same = 0
        for row in rows:
            if row["same"]:
                same += 1
        print("  → 일치율:", same, "/", len(rows), "=", round(same * 100.0 / len(rows), 1), "%")
