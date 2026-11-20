# 목적: 사이즈 추천 본체 — 입력 검사 → 몸 치수 추정 → 사이즈별 여유분 → 선호 핏으로 고르기 → 설명용 근거 정리
# FigJam "04 / AZURE LOGIC" 의 03 사이즈 계산 단계 ("초기: 비교 규칙 엔진 → 확장: Azure ML 모델")
#
# 팀 코드를 그대로 쓰는 곳 (team_bridge 로 import):
#   team_check.validate   입력값 검사                       (db/예시_코드/_검증.py)
#   team_est.estimate      키·체중 → 몸 치수 k-NN 추정        (db/예시_코드/_추정.py, DB 모드)
#   team_rec.ease_for_size 여유분 = 옷 치수 × factor − 몸 치수  (db/예시_코드/_추천.py)
#   team_rec.rank_key      팀 기준선 순위 (fit 먼저, 평균 여유분 작은 순)
# 이 파일이 더하는 것: 잘 맞는 내 옷과 비교 · 화면/AI 설명용 근거(facts)
# 몸 기준 사이즈 선택은 팀 판정 기준 ease_check(ease_rules) 한 곳에서 한다. 여기에는 판정 기준값을 두지 않는다.
import catalog
import demo_data
import ease_rules
from team_bridge import team_check, team_est, team_rec

GIRTH_CODES = ("chest_girth", "waist_girth", "hip_girth")
# 사이즈 결정에 쓰는 항목. 나머지(팔길이↔소매길이 등)는 측정 기준이 달라 표에만 참고로 보여 줌
DECIDING_CODES = GIRTH_CODES + ("shoulder_width",)

# 잘 맞는 내 옷의 실측으로 받을 수 있는 항목 (옷 기준 코드)
MY_GARMENT_CODES = ("chest_width", "garment_shoulder_width", "body_length", "sleeve_length")


# 목적: 숫자로 바꾸기 (빈칸이면 None)
def _number(value):
    if value is None or str(value).strip() == "":
        return None
    return float(value)


# 목적: 잘 맞는 내 옷 실측 검사 → ({코드: cm}, 오류 목록)
def _clean_my_garment(raw):
    mine, errors = {}, []
    for code in MY_GARMENT_CODES:
        value = (raw or {}).get(code)
        if value is None or str(value).strip() == "":
            continue
        try:
            number = float(value)
        except ValueError:
            errors.append("내 옷 " + code + ": 숫자가 아님")
            continue
        if number < 10 or number > 150:
            errors.append("내 옷 " + code + ": 10 ~ 150cm 범위 밖")
            continue
        mine[code] = round(number, 1)
    return mine, errors


# 목적: 몸 치수 추정. DB 모드 = 팀 k-NN, 데모 모드 = 데모 식
def _estimate_body(mode, gender, height_cm, weight_kg):
    if mode == "db":
        rows = team_est.estimate(gender, height_cm, weight_kg)
        return team_est.to_body(rows), team_rec.measure_maps(), "팀 k-NN 추정(" + team_est.MODEL_VERSION + ")"
    return demo_data.estimate_body(gender, height_cm, weight_kg), demo_data.MEASURE_MAPS, "데모 추정식(검증 전)"


# 목적: 사이즈 하나 평가 → 여유분·상태·내 옷과 차이
def _score_size(size, body, maps, mine):
    team_size = {"garment": {code: team_rec.to_dec(v) for code, v in size["garment"].items()}}
    eases = {code: team_rec.round1(v) for code, v in team_rec.ease_for_size(team_size, body, maps).items()}
    deciding = {c: v for c, v in eases.items() if c in DECIDING_CODES}
    if len(size["garment"]) == 0:
        status = "nodata"
    elif len(deciding) == 0:
        status = "nocompare"
    elif min(deciding.values()) >= 0:
        status = "fit"
    else:
        status = "small"
    diff_mine = {}
    for code in mine:
        if code in size["garment"]:
            diff_mine[code] = round(size["garment"][code] - mine[code], 1)
    return {"size_label": size["size_label"], "garment": size["garment"], "ease": eases,
            "status": status, "diff_vs_mine": diff_mine, "body_range": size.get("body_range", {})}


# 목적: 몸 기준으로 고르기 — ease_check 가 입을 수 있다고 판정한 사이즈 중 추천(가장 몸에 가까운 것)
def _pick_by_body(scored, body, category):
    rows = [{"size_label": s["size_label"], "measure_code": "chest_width", "basis": "garment",
             "value_cm": float(s["garment"]["chest_width"])} for s in scored if "chest_width" in s["garment"]]
    chest = body.get("chest_girth")
    judged = ease_rules.judge_sizes(category, None if chest is None else float(chest), rows, None)
    chosen = next((s for s in scored if s["size_label"] == judged["recommended_size"]), None)
    if chosen is None:
        return None, "팀 판정 기준(ease_check)으로 입을 수 있는 사이즈가 없어요.", judged
    return chosen, None, judged


# 목적: 내 옷 기준으로 고르기 — 내 옷과 치수 차이(절댓값 평균)가 가장 작은 사이즈
def _pick_by_mine(scored):
    best, best_gap = None, None
    for s in scored:
        if len(s["diff_vs_mine"]) == 0:
            continue
        gap = sum(abs(v) for v in s["diff_vs_mine"].values()) / len(s["diff_vs_mine"])
        if best_gap is None or gap < best_gap:
            best, best_gap = s, gap
    return best


# 목적: 팀 _추천.py 의 기준선 순위로 1등 (화면에 "팀 규칙 기준선"으로 같이 보여 줌 → ML 비교용)
def _team_baseline(scored):
    ranked = []
    for s in scored:
        values = list(s["ease"].values())
        if len(values) == 0:
            continue
        ranked.append({"label": s["size_label"], "min_ease": min(values), "avg_ease": sum(values) / len(values)})
    if len(ranked) == 0:
        return None
    ranked.sort(key=team_rec.rank_key)
    return ranked[0]["label"]


# 목적: 비교 상대 사이즈 (추천 바로 위 사이즈, 없으면 바로 아래)
def _neighbor(scored, label):
    usable = [s for s in scored if s["status"] != "nodata"]
    labels = [s["size_label"] for s in usable]
    i = labels.index(label)
    if i + 1 < len(usable):
        return usable[i + 1]
    if i - 1 >= 0:
        return usable[i - 1]
    return None


# 목적: 화면 요청(dict) → 추천 결과(dict). main.py 의 POST /api/recommend 가 부름
def recommend(req):
    gender = req.get("gender")
    form = {"gender": gender, "height_cm": req.get("height_cm"), "weight_kg": req.get("weight_kg")}
    entered = {k: v for k, v in (req.get("measures") or {}).items() if str(v).strip() != ""}
    if len(entered) > 0:
        form["measures"] = entered
    errors = team_check.validate(form, need_account=False)
    mine, mine_errors = _clean_my_garment(req.get("my_garment"))
    errors += mine_errors
    if len(errors) > 0:
        return {"ok": False, "status": "invalid", "errors": errors}

    found = catalog.find_product(req.get("item_code", ""), req.get("region") or "KR")
    if not found["ok"]:
        return {"ok": False, "status": "not_found", "errors": [found["error"]]}
    product, mode = found["product"], found["mode"]
    if not product["can_recommend"]:
        return {"ok": False, "status": "hold", "mode": mode, "product": product,
                "errors": ["이 상품은 아직 사이즈별 실측이 없어 추천을 보류해요. (Data 담당: garment.measures 확보 필요)"]}

    height_cm, weight_kg = float(req["height_cm"]), float(req["weight_kg"])
    body, maps, estimator = _estimate_body(mode, gender, height_cm, weight_kg)
    body_source = {code: "estimated" for code in body}
    for code, value in entered.items():
        body[code] = float(value)
        body_source[code] = "entered"

    scored = [_score_size(size, body, maps, mine) for size in product["sizes"]]
    warnings = []
    if len(product["missing_sizes"]) > 0:
        warnings.append("실측 자료가 없는 사이즈는 비교에서 뺐어요: " + ", ".join(product["missing_sizes"]))

    basis = "body"
    chosen, note, judged = None, None, None
    if len(mine) > 0:
        chosen = _pick_by_mine(scored)
        if chosen is not None:
            basis = "my_garment"
    if chosen is None:
        chosen, note, judged = _pick_by_body(scored, body, product.get("category") or "상의")
    if chosen is None:
        return {"ok": False, "status": "hold", "mode": mode, "product": product, "ease_check": judged,
                "errors": [judged["selected"]["message_ko"] if judged and not judged["all_sizes"] else note]}

    other = _neighbor(scored, chosen["size_label"])
    names = catalog.measure_names()
    return {
        "ok": True, "status": "done", "mode": mode, "product": product,
        "input": {"gender": gender, "height_cm": height_cm, "weight_kg": weight_kg, "my_garment": mine},
        "estimator": estimator,
        "body_used": {code: {"value_cm": body[code], "source": body_source[code]} for code in sorted(body)},
        "maps": [{"body": m["body_measure_code"], "garment": m["garment_measure_code"], "factor": float(m["factor"])} for m in maps],
        "sizes": scored,
        "recommended": chosen["size_label"],
        "compare_with": other["size_label"] if other else None,
        "basis": basis,
        "team_baseline": _team_baseline(scored),
        "rule": {"rules_version": ease_rules.rules_version(), "deciding_codes": list(DECIDING_CODES)},
        "ease_check": judged,
        "measure_names": names,
        "warnings": warnings,
    }
