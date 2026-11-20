# 목적: 화면·API 가 부를 추천 함수 — 요청(dict) → 입력 검사 → 치수 추정 → 사이즈 추천 → 응답(JSON)
# 누가 쓰나: 프론트
# 난이도: 고급 — 검사(_검증.py) → k-NN 추정(_추정.py) → 규칙 추천(_추천.py) 를 한 API 로 묶기
# 출력: 추천 응답 JSON 2개(estimate 22개·body_used·sizes M·recommended_size null 메시지), 틀린 입력 errors
# 실행: .venv/bin/python db/예시_코드/front/3_고급/10_추천_요청_처리.py
# DB 에 쓰지 않음 (조회만). 저장까지 하려면 front/3_고급/05_사용자_신체정보_저장.py 의 register(..., method="estimated")
import json
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _추정 import estimate, to_body, MODEL_VERSION    # k-NN 치수 추정 (예시_코드/_추정.py)
from _추천 import recommend                           # 규칙 사이즈 추천 (예시_코드/_추천.py)
from _검증 import validate                            # 입력 검사 (예시_코드/_검증.py)

# 옷을 안 고르면 쓰는 기본값: UNIQLO 크루넥T(unisex). 예시 DB 에서 옷 실측이 있는 사이즈는 KR M / US M
DEFAULT_SOURCE = "uniqlo_site"
DEFAULT_ITEM = "E422992-000"
DEFAULT_REGION = "US"

ESTIMATE_NOTE = "기준선 추정: 예시 DB 는 실측자가 적어 오차가 큼. ANSUR II / BodyM 전체 적재 후 더 정확해짐"


# 목적: 요청에 값이 없으면 기본값
def get_or_default(request, key, default):
    if key in request and request[key] is not None and str(request[key]).strip() != "":
        return request[key]
    return default


# 목적: 추천 표 한 행 → 응답용 모양 {"size_label", "ease_cm": {코드: 값}, "avg_ease_cm", "size_status", "rank", "body_range"}
def size_to_response(row):
    ease = {}
    for key in row:
        if key.startswith("여유:"):
            ease[key[len("여유:"):]] = row[key]
    return {
        "size_label": row["size_label"],
        "ease_cm": ease,
        "avg_ease_cm": row["avg_ease"],
        "size_status": row["size_status"],
        "rank": row["rank"],
        "body_range": row["권장범위"],
    }


# 목적: API 본체: 요청 dict → 응답 dict (ok=False 면 errors 에 이유)
def handle_recommend(request):
    # 1) 입력 검사 (회원 정보는 필요 없음)
    errors = validate(request, need_account=False)
    if len(errors) > 0:
        return {"ok": False, "errors": errors}

    gender = request["gender"]
    height_cm = float(request["height_cm"])
    weight_kg = float(request["weight_kg"])
    source_name = get_or_default(request, "source_name", DEFAULT_SOURCE)
    item_code = get_or_default(request, "item_code", DEFAULT_ITEM)
    region = get_or_default(request, "region", DEFAULT_REGION)

    # 2) 치수 추정. 사용자가 직접 잰 치수(measures)가 있으면 추정값 대신 그 값을 씀
    estimated = estimate(gender, height_cm, weight_kg)
    body = to_body(estimated)
    measured = request.get("measures")
    if measured is not None:
        for code in measured:
            body[code] = float(measured[code])
    if len(body) == 0:
        return {"ok": False, "errors": ["estimate: 이 성별로 추정할 실측 자료가 없음"]}

    # 3) 사이즈 추천 (_추천.py 규칙)
    table = recommend(body, source_name, item_code, region, verbose=False)
    sizes = []
    for row in table:
        sizes.append(size_to_response(row))

    recommended = None
    message = "비교할 수 있는 치수가 없음"
    if len(sizes) > 0 and sizes[0]["rank"] != "-":
        if sizes[0]["size_status"] == "fit":
            recommended = sizes[0]["size_label"]
            message = "추천 사이즈 " + str(recommended)
        else:
            message = "맞는 사이즈 없음 (모두 small). 가장 가까운 사이즈 " + str(sizes[0]["size_label"])

    return {
        "ok": True,
        "input": {"gender": gender, "height_cm": height_cm, "weight_kg": weight_kg},
        "estimate": {"model_version": MODEL_VERSION, "note": ESTIMATE_NOTE, "measures": estimated},
        "body_used": body,
        "garment": {"source_name": source_name, "item_code": item_code, "region": region},
        "sizes": sizes,
        "recommended_size": recommended,
        "message": message,
    }


# 목적: 응답을 JSON 글자로 출력 (한글 그대로)
def print_json(title, data):
    print()
    print("■ " + title)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    ok_request = {"gender": "male", "height_cm": 175.0, "weight_kg": 75.0,
                  "source_name": "uniqlo_site", "item_code": "E422992-000", "region": "US"}
    print_json("요청 1 (올바른 입력)", ok_request)
    print_json("응답 1", handle_recommend(ok_request))

    measured_request = {"gender": "male", "height_cm": 177.6, "weight_kg": 81.5, "region": "US",
                        "measures": {"chest_girth": 107.4, "shoulder_width": 40.1}}
    print_json("요청 2 (직접 잰 가슴·어깨 포함, 옷은 기본값)", measured_request)
    print_json("응답 2", handle_recommend(measured_request))

    bad_request = {"gender": "man", "height_cm": "abc", "weight_kg": 75.0}
    print_json("요청 3 (틀린 입력)", bad_request)
    print_json("응답 3", handle_recommend(bad_request))
