"""판매 중인 특정 옷 한 벌의 거래 전 핏 판단. 옷 실측과 구매자 신체 치수를 분리한다."""
import math
from typing import Annotated, Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pymysql import MySQLError

import demo_data
import ease_rules
import sizing
import team_bridge
from team_bridge import team_check, team_rec

router = APIRouter(prefix="/api/resale")
Label = Annotated[str, Field(min_length=1, max_length=80)]
Cm = Annotated[float, Field(strict=True, gt=0, le=400, allow_inf_nan=False)]
Source = Literal["카탈로그", "예시 카탈로그", "시연용 예시", "직접 실측", "판매글 실측", "ML 추정", "ML 결과 파일"]
Category = Literal["상의·아우터", "하의", "원피스"]
REFERENCE_TOLERANCE_CM = 2.0  # 팀 검증 전, 동일 부위 평면 치수 비교에 쓰는 시연 기준
# 신체 기준 착용 판정은 ease_check(ease_rules) 한 곳에서만 한다. 여기에는 판정 기준값을 두지 않는다.
REQUIRED = {"상의·아우터": ("가슴단면",), "하의": ("허리단면",), "원피스": ("가슴단면", "허리단면")}
REFERENCE_PARTS = {
    "상의·아우터": {"가슴단면", "어깨너비", "총장", "소매길이", "허리단면"},
    "하의": {"허리단면", "엉덩이단면", "허벅지단면", "무릎단면", "밑단단면", "총장", "안쪽기장", "밑위", "앞밑위", "뒤밑위"},
    "원피스": {"가슴단면", "허리단면", "엉덩이단면", "어깨너비", "총장", "소매길이"},
}
BODY_PARTS = {
    "가슴단면": ("chest_width", "chest_girth", "가슴둘레"),
    "허리단면": ("waist_width", "waist_girth", "허리둘레"),
    "엉덩이단면": ("hip_width", "hip_girth", "엉덩이둘레"),
    "어깨너비": ("garment_shoulder_width", "shoulder_width", "어깨너비"),
}


class BuyerBody(BaseModel):
    gender: Literal["male", "female"] | None = None
    height_cm: Annotated[float, Field(ge=team_check.HEIGHT_MIN, le=team_check.HEIGHT_MAX)] | None = None
    weight_kg: Annotated[float, Field(ge=team_check.WEIGHT_MIN, le=team_check.WEIGHT_MAX)] | None = None
    measures: dict[Literal["chest_girth", "waist_girth", "hip_girth", "shoulder_width"],
                   Annotated[float, Field(strict=True, ge=team_check.MEASURE_MIN, le=team_check.MEASURE_MAX)]] = Field(default_factory=dict)
    source: str = Field(default="입력한 신체 치수", min_length=1, max_length=60)


class ListingFitRequest(BaseModel):
    category: Category
    rows: list[tuple[Label, Cm, Source]] = Field(max_length=32)
    my_garment: dict[Label, Cm] = Field(default_factory=dict, max_length=32)
    body: BuyerBody | None = None

    @model_validator(mode="after")
    def unique_rows(self):
        if len({name for name, _, _ in self.rows}) != len(self.rows):
            raise ValueError("옷의 같은 부위는 한 번만 입력해 주세요.")
        return self


def _result(status, basis, title, explanation, evidence, notes):
    return {"status": status, "basis": basis, "title": title, "explanation": explanation,
            "evidence": evidence, "notes": notes}


def _source_notes(evidence):
    sources = {row["source"] for row in evidence}
    notes = []
    if "카탈로그" in sources or "예시 카탈로그" in sources:
        notes.append("세탁이나 수선으로 현재 판매 옷과 카탈로그 치수가 달라질 수 있어요.")
    if "예시 카탈로그" in sources:
        notes.append("예시 카탈로그 치수를 사용한 시연 결과예요.")
    if "시연용 예시" in sources:
        notes.append("이 매물의 치수는 사용 방법을 보여 주기 위한 예시예요.")
    if {"ML 추정", "ML 결과 파일"} & sources:
        notes.append("촬영 기반 ML 측정값에는 오차가 있을 수 있어요.")
    return notes


def _compare_reference(request, evidence):
    notes = _source_notes(evidence)
    names = {row["name"] for row in evidence}
    missing = [name for name in REQUIRED[request.category] if name not in names]
    if missing:
        needed = ", ".join(missing)
        if len(evidence) == 1 and evidence[0]["name"] in REQUIRED[request.category]:
            return _result("hold", "my_garment", evidence[0]["description"],
                           f"이 부위만 비교했어요. 옷 전체의 핏을 보려면 {needed}도 확인해 주세요.", evidence, notes)
        return _result("hold", "my_garment", "사이즈 추천 보류",
                       f"판매 옷과 잘 맞는 옷의 {needed} 치수가 있어야 핏을 비교할 수 있어요.", evidence, notes)

    notes.append(f"같은 종류의 옷을 펼쳐 잰 치수 차이 ±{REFERENCE_TOLERANCE_CM:g} cm를 비슷한 범위로 보는 임시 기준이에요.")
    largest = max(evidence, key=lambda row: abs(row["difference_cm"]))
    if abs(largest["difference_cm"]) > REFERENCE_TOLERANCE_CM:
        return _result("check", "my_garment", f"{largest['name']} 차이를 확인하세요",
                       largest["description"] + " 원하는 핏인지 확인한 뒤 거래하세요.", evidence, notes)
    return _result("recommended", "my_garment", "비교한 치수 기준으로 추천해요",
                   "판매 옷과 잘 맞는 옷에서 입력한 부위가 모두 비슷한 범위에 있어요.", evidence, notes)


def _reference_evidence(request):
    evidence = []
    for name, value, source in request.rows:
        if name not in REFERENCE_PARTS[request.category] or name not in request.my_garment:
            continue
        mine = request.my_garment[name]
        delta = team_rec.round1(team_rec.to_dec(value) - team_rec.to_dec(mine))
        text = (f"{name}은 내 옷과 같아요." if delta == 0 else
                f"{name}은 내 옷보다 {abs(delta):g} cm {'커요' if delta > 0 else '작아요'}.")
        evidence.append({"name": name, "garment_cm": value, "compared_garment_cm": value, "source": source,
                         "reference_cm": mine, "difference_cm": delta, "description": text})
    return evidence


def _body_evidence(request, values, maps, estimated=False):
    allowed = {"상의·아우터": ("가슴단면", "어깨너비"), "하의": ("허리단면", "엉덩이단면"),
               "원피스": tuple(BODY_PARTS)}[request.category]
    garments = {BODY_PARTS[name][0]: team_rec.to_dec(cm) for name, cm, _ in request.rows if name in allowed}
    eases = team_rec.ease_for_size({"garment": garments}, values, maps)
    factors = {(row["garment_measure_code"], row["body_measure_code"]): float(row["factor"]) for row in maps}
    evidence = []
    for name, cm, source in request.rows:
        if name not in allowed:
            continue
        code, body_code, body_name = BODY_PARTS[name]
        if body_code not in eases or (code, body_code) not in factors:
            continue
        factor = factors[code, body_code]
        compared_cm = team_rec.round1(team_rec.to_dec(cm) * team_rec.to_dec(factor))
        ease = team_rec.round1(eases[body_code])
        conversion = f" × {factor:g}" if factor != 1 else ""
        reference_display = team_rec.round1(team_rec.to_dec(values[body_code]))
        qualifier = "추정 " if estimated else ""
        text = f"{name} {cm:g}{conversion} − {qualifier}{body_name} {reference_display:g} = 여유 {ease:g} cm"
        evidence.append({"name": name, "garment_cm": cm, "source": source, "compared_garment_cm": compared_cm,
                         "reference_cm": values[body_code], "difference_cm": ease, "description": text})

    return evidence


_VERDICT_STATUS = {"FIT": "recommended", "NO_FIT": "check"}


def _ease_listing(request, body_chest, evidence, notes, hold):
    """이 옷 한 벌의 가슴단면을 ease_check 로 판정한다. 결과 문구는 message_ko 를 그대로 쓴다."""
    if request.category != "상의·아우터":
        return hold("하의·원피스는 아직 판정하지 않아요",
                    "팀 판정 기준(ease_check)은 상의 가슴둘레만 판정해요. 잘 맞는 내 옷의 같은 부위와 비교해 주세요.",
                    evidence, notes)
    width = next((cm for name, cm, _ in request.rows if name == "가슴단면"), None)
    if width is None or body_chest is None:
        return hold("사이즈 추천 보류", "판매 옷의 가슴단면과 구매자의 가슴둘레 정보가 필요해요.", evidence, notes)
    judged = ease_rules.judge_sizes(request.category, body_chest, [
        {"size_label": "이 옷", "measure_code": "chest_width", "basis": "garment", "value_cm": width}], "이 옷")
    selected = judged["selected"]
    result = _result(_VERDICT_STATUS.get(selected["verdict"], "hold"), "body", selected["message_ko"], "", evidence, notes)
    result["ease_check"] = selected
    return result


def _quick_comparison(request):
    """옷 실측과 체격이 비슷한 실측 표본의 산포로 부위별 핏을 판단한다."""
    required = REQUIRED[request.category]
    seller_parts = {name for name, _, _ in request.rows}

    def hold(title, detail, evidence, notes, reference=None):
        result = _result("hold", "body", title, detail, evidence, notes)
        reference = reference or next((part for part in required if part in seller_parts), None)
        if reference:
            result["reference_field"] = reference
        return result

    missing = [name for name in required if name not in seller_parts]
    if missing:
        return hold("옷 실측이 더 필요해요",
                    f"이 매물에 {', '.join(missing)} 치수가 없어 전체 핏을 판단하기 어려워요.", [], [])
    try:
        values, spreads, counts, maps, source = team_bridge.estimate_from_height_weight(
            request.body.height_cm, request.body.weight_kg)
    except (MySQLError, RuntimeError):
        return hold("핏을 아직 확인할 수 없어요", "신체 실측 자료를 불러오지 못했어요. 잠시 후 다시 확인해 주세요.", [], [])

    evidence = _body_evidence(request, values, maps, estimated=True)
    notes = _source_notes(evidence)
    notes.append(f"{source}에서 키·몸무게가 가까운 사람에게 더 큰 비중을 두었어요. 참고 범위는 부위별 평균에서 표준편차 한 배만큼의 폭이에요. 실제 착용으로 검증하기 전의 추정이에요.")
    parts = {"가슴단면": "가슴", "허리단면": "허리", "엉덩이단면": "엉덩이", "어깨너비": "어깨"}
    for row in evidence:
        name = row["name"]
        code = BODY_PARTS[name][1]
        average_ease = row["compared_garment_cm"] - values[code]
        low = math.floor(average_ease - spreads[code])
        high = math.ceil(average_ease + spreads[code])
        row.update(reference_cm=round(values[code], 1), ease_range_cm=[low, high], reference_count=counts[code],
                   description=f"{parts[name]} 여유 참고 범위는 약 {low}~{high} cm예요. 비슷한 체격 {counts[code]}명의 실측을 참고했어요.")
    if not any(row["name"] in required for row in evidence):
        return hold("비슷한 체격의 자료가 더 필요해요", "현재 표본으로는 이 옷의 핏을 추정하기 어려워요.", evidence, notes)
    chest, spread = values.get("chest_girth"), spreads.get("chest_girth", 0)
    body_chest = None if chest is None else {"value": float(chest), "lo": float(chest) - float(spread),
                                             "hi": float(chest) + float(spread)}
    return _ease_listing(request, body_chest, evidence, notes, hold)


def _compare_body(request):
    profile = request.body
    values = profile.measures
    estimator = profile.source
    maps = demo_data.MEASURE_MAPS
    if not values and profile.height_cm is not None and profile.weight_kg is not None:
        if profile.gender is None:
            return _quick_comparison(request)
        mode = team_bridge.current_mode()
        values, maps, estimator = sizing._estimate_body(mode, profile.gender, profile.height_cm, profile.weight_kg)
    elif values and team_bridge.current_mode() == "db":
        maps = team_rec.measure_maps()

    evidence = _body_evidence(request, values, maps)
    notes = _source_notes(evidence)
    if evidence:
        notes.append(f"구매자 신체 기준은 {estimator}입니다.")
    def hold(title, detail, evidence, notes):
        return _result("hold", "body", title, detail, evidence, notes)
    chest = values.get("chest_girth")
    return _ease_listing(request, None if chest is None else float(chest), evidence, notes, hold)


@router.post("/recommend")
def recommend_listing(request: ListingFitRequest):
    evidence = _reference_evidence(request)
    if evidence:
        result = _compare_reference(request, evidence)
        if result["status"] != "hold" or not request.body:
            return result
        if (request.body.gender is None and not request.body.measures
                and any(row["name"] in REQUIRED[request.category] for row in evidence)):
            # 한 부위만 비교해도 그 차이는 보존하고, 원피스 전체에 대한 판단은 유보한다.
            return result
        body_result = _compare_body(request)
        if body_result["status"] != "hold":
            body_result["notes"].append("내 옷과 비교할 핵심 단면 치수가 없어 신체 치수를 기준으로 판단했어요.")
            return body_result
        return result
    if request.rows and request.body:
        return _compare_body(request)
    message = ("가슴단면이나 허리단면 등 판매 옷의 의류 실측을 먼저 확인해 주세요." if not request.rows
               else "내 옷의 같은 부위 치수나 구매자의 신체 정보를 입력해 주세요.")
    return _result("hold", None, "사이즈 추천 보류", message, [], [])


class EaseRequest(BaseModel):
    """구매자 피팅룸: 한 상품의 모든 사이즈를 키·몸무게로 추정한 가슴둘레와 ease_check 로 판정한다."""
    model_config = ConfigDict(extra="forbid")
    garment_id: int = Field(gt=0, lt=2 ** 31)
    category: Annotated[str, Field(min_length=1, max_length=20)]
    region: Annotated[str, Field(min_length=1, max_length=8)] = "KR"
    size_label: Label
    height_cm: Annotated[float, Field(ge=team_check.HEIGHT_MIN, le=team_check.HEIGHT_MAX)]
    weight_kg: Annotated[float, Field(ge=team_check.WEIGHT_MIN, le=team_check.WEIGHT_MAX)]


def ease_sizes(request: EaseRequest):
    import resale
    chart = resale.size_chart(request.garment_id)
    rows = [{"size_label": size["label"], "region": size.get("region"), "measure_code": "chest_width",
             "basis": "garment", "value_cm": size["measures"]["가슴단면"]}
            for size in chart.get("sizes", []) if "가슴단면" in (size.get("measures") or {})]
    try:
        values, spreads, counts, _maps, source = team_bridge.estimate_from_height_weight(request.height_cm, request.weight_kg)
    except (MySQLError, RuntimeError):
        return ease_rules.undetermined("신체 자료를 불러오지 못했습니다.", request.size_label)
    chest = values.get("chest_girth")
    if chest is None:
        return ease_rules.undetermined("키·몸무게로 가슴둘레를 추정하지 못했습니다.", request.size_label)
    spread = float(spreads.get("chest_girth", 0))
    korean = request.region == "KR"
    result = ease_rules.judge_sizes(request.category, {"value": float(chest), "lo": float(chest) - spread,
                                                       "hi": float(chest) + spread}, rows,
                                    request.size_label if korean else None)
    if not korean:
        result["selected"] = ease_rules.undetermined("판정은 KR 사이즈 기준으로만 합니다.", request.size_label)["selected"]
    result["body"] = {"chest_girth_cm": round(float(chest), 1), "basis": "키·몸무게로 추정", "source": source,
                      "reference_count": counts.get("chest_girth")}
    return result
