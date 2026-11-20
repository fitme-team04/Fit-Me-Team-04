# 목적: 추천 이유를 쉬운 문장으로 — Azure OpenAI 가 설정돼 있으면 AI 문장, 아니면 템플릿 문장
# FigJam "03 / EXPLAIN" 원칙: 언어모델은 실측값이나 추천을 "만들지 않고", 계산된 결과를 "설명만" 한다
#   ① 계산 결과(facts)만 AI 에 넘김  ② JSON 모양으로 받음  ③ 결과에 facts 에 없는 숫자가 있으면 버리고 템플릿 사용
import json
import re

import settings


# 목적: 추천 결과 → 설명에 쓸 근거 목록 (사람이 읽는 문장 + 숫자). AI 와 템플릿이 같은 근거를 씀
def build_facts(result):
    names = result["measure_names"]
    sizes = {s["size_label"]: s for s in result["sizes"]}
    rec = sizes[result["recommended"]]
    facts = []

    if result["basis"] == "my_garment":
        for code, diff in rec["diff_vs_mine"].items():
            facts.append({"kind": "vs_mine", "name": names.get(code, code),
                          "mine_cm": result["input"]["my_garment"][code], "size_cm": rec["garment"][code], "diff_cm": diff})
    else:
        factors = {m["body"]: (m["garment"], m["factor"]) for m in result["maps"]}
        for code, ease in rec["ease"].items():
            g_code, factor = factors[code]
            facts.append({"kind": "ease", "name": names.get(code, code),
                          "body_cm": result["body_used"][code]["value_cm"],
                          "body_source": result["body_used"][code]["source"],
                          "garment_name": names.get(g_code, g_code), "garment_cm": rec["garment"][g_code],
                          "factor": factor, "ease_cm": ease, "decides": code in result["rule"]["deciding_codes"]})

    if result["compare_with"]:
        other = sizes[result["compare_with"]]
        for code in ("chest_width", "garment_shoulder_width", "body_length"):
            if code in rec["garment"] and code in other["garment"]:
                facts.append({"kind": "compare", "name": names.get(code, code), "size": result["compare_with"],
                              "from_cm": rec["garment"][code], "to_cm": other["garment"][code],
                              "diff_cm": round(other["garment"][code] - rec["garment"][code], 1)})
    return facts


def _signed(value):
    return ("+" if value > 0 else "") + str(value)


# 목적: AI 없이 만드는 기본 설명 (AI 실패 시에도 이걸 보여 줌 → FigJam "계산 결과와 실측 표는 그대로 제공")
# 문장을 바꿔 보려면 여기 summary·points 글자를 고치고 저장 → 개발 모드(windows_app.cmd)면 바로 반영
def template_explanation(result, facts):
    rec = result["recommended"]
    if result["basis"] == "my_garment":
        summary = "잘 맞는 내 옷과 치수가 가장 비슷한 " + rec + " 사이즈를 추천해요."
    else:
        summary = "팀 판정 기준으로 입을 수 있는 사이즈 중 몸에 가장 가까운 " + rec + " 사이즈를 추천해요."
    points = []
    compare = []
    for f in facts:
        if f["kind"] == "vs_mine":
            points.append(f["name"] + ": 내 옷 " + str(f["mine_cm"]) + "cm, " + rec + " " + str(f["size_cm"]) + "cm (" + _signed(f["diff_cm"]) + "cm)")
        elif f["kind"] == "ease" and f["decides"]:
            label = "내 " if f["body_source"] == "entered" else "추정 "
            if f["factor"] == 1:
                garment_txt = "옷 " + f["garment_name"] + " " + str(f["garment_cm"]) + "cm"
            else:
                garment_txt = "옷 둘레 " + str(round(f["garment_cm"] * f["factor"], 1)) + "cm(" + f["garment_name"] + " " + str(f["garment_cm"]) + "×" + str(int(f["factor"])) + ")"
            points.append(f["name"] + ": " + label + str(f["body_cm"]) + "cm, " + garment_txt + " → 여유 " + _signed(f["ease_cm"]) + "cm")
        elif f["kind"] == "compare":
            compare.append(f["name"] + " " + _signed(f["diff_cm"]))
    if len(compare) > 0:
        points.append(result["compare_with"] + " 사이즈와 비교하면 " + " · ".join(compare) + "cm")
    ask_more = None
    if result["basis"] == "body" and len(result["input"]["my_garment"]) == 0:
        ask_more = "잘 맞는 옷의 실측(가슴단면·어깨너비·총장)을 넣으면 내 옷과 직접 비교해 드려요."
    return {"source": "template", "summary": summary, "points": points[:5], "ask_more": ask_more}


# 목적: 근거 안의 숫자 모음 (AI 문장 검증용)
def _allowed_numbers(result, facts):
    allowed = {0.0, 1.0, 2.0, 3.0}
    text = json.dumps(facts, ensure_ascii=False) + json.dumps(result["input"], ensure_ascii=False)
    for token in re.findall(r"\d+(?:\.\d+)?", text):
        allowed.add(round(float(token), 1))
    return allowed


# 목적: AI 문장 검사 — 근거에 없는 숫자가 하나라도 있으면 실패
def _numbers_ok(answer, allowed):
    text = answer["summary"] + " " + " ".join(answer["points"]) + " " + (answer.get("ask_more") or "")
    text = re.sub(r"\b\d?X{0,3}[SML]\b", "", text)       # 사이즈 이름(3XL 등)은 숫자 검사에서 뺌
    for token in re.findall(r"\d+(?:\.\d+)?", text):
        if round(float(token), 1) not in allowed:
            return False
    return True


SYSTEM_PROMPT = """너는 옷 사이즈 추천 앱 '입어봄'의 설명 도우미야.
규칙:
- 아래 JSON 의 추천 결과와 근거(facts)만 사용해서 한국어로 쉽게 설명해.
- 새로운 숫자, 확률, 치수를 절대 만들지 마. 근거에 있는 숫자만 그대로 써.
- 추천 사이즈를 바꾸지 마. 착용감을 보장하는 표현은 쓰지 마.
- 근거가 부족하면 ask_more 에 사용자에게 물어볼 한 문장을 적어.
반드시 이 JSON 모양으로만 답해: {"summary": "한 문장", "points": ["짧은 문장", "...최대 4개"], "ask_more": "문장 또는 null"}"""


# 목적: Azure OpenAI 호출 → 설명 dict (실패하면 예외)
def _azure_explanation(result, facts):
    from openai import AzureOpenAI          # Azure OpenAI 를 쓸 때만 필요한 패키지
    client = AzureOpenAI(azure_endpoint=settings.AZURE_OPENAI_ENDPOINT, api_key=settings.AZURE_OPENAI_API_KEY,
                         api_version=settings.AZURE_OPENAI_API_VERSION, timeout=20)
    payload = {"recommended": result["recommended"], "compare_with": result["compare_with"],
               "basis": result["basis"], "facts": facts}
    response = client.chat.completions.create(
        model=settings.AZURE_OPENAI_DEPLOYMENT,
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        response_format={"type": "json_object"},
    )
    answer = json.loads(response.choices[0].message.content)
    answer = {"summary": str(answer.get("summary", "")), "points": [str(p) for p in answer.get("points", [])][:4],
              "ask_more": answer.get("ask_more")}
    if answer["summary"] == "" or not _numbers_ok(answer, _allowed_numbers(result, facts)):
        raise ValueError("AI 설명에 근거에 없는 숫자가 있거나 비어 있음")
    answer["source"] = "azure_openai"
    return answer


# 목적: 화면이 받는 설명 — AI 시도 → 실패하면 템플릿 (실패 이유는 note 에 남김)
def explain(result):
    facts = build_facts(result)
    fallback = template_explanation(result, facts)
    if not settings.ai_configured():
        fallback["note"] = "Azure OpenAI 미설정 — 템플릿 설명"
        return fallback
    try:
        return _azure_explanation(result, facts)
    except Exception as exc:
        fallback["note"] = "AI 설명 실패 → 템플릿 사용 (" + type(exc).__name__ + ")"
        return fallback
