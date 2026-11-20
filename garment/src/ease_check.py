# 역할: 상품 실측과 ML 예측 둘레를 비교해 사이즈별 여유분과 추천 사이즈를 판정합니다.
"""ease_check.py - 여유분(옷 - 몸)만으로 "입을 수 있다 / 못 입는다"를 판정하는 단일 파일 모듈

규칙 (팀 결정: 최소 2026-11-12, 최대 2026-11-16)
  - 슬림/스탠다드/오버핏 구분은 쓰지 않는다.
  - 여유분 = 옷 실측 둘레 - 몸 둘레 (cm)
  - 부위마다  최소(3cm) <= 여유분 <= 최대  이면 맞다 (FIT)
      여유분 <  최소 → 작아서 못 입는다 (NO_FIT, 부위 status TOO_TIGHT)
      여유분 >  최대 → 커서 안 맞는다   (NO_FIT, 부위 status TOO_LOOSE)
  - 최대값: 상의 가슴 20cm / 하의 엉덩이 15cm / 하의 허리 상한 없음
  - 판정할 값이 없거나 비정상 → 판정 불가 (UNDETERMINED). 데이터가 없을 때 임의로 FIT을 내지 않는다.
  ※ 최소·최대 모두 공인 표준(ISO 8559-1, KS K 0050)에는 없는 값이며, 아래 논문 범위를 참고한 팀 운영값이다.
    근거·출처는 EASE_LIMITS_CM 주석과 EASE_CHECK_README.md '2-1. 기준값의 근거'를 본다.

판정 부위
  - 상의(top)   : 가슴둘레 chest_girth_cm                         → 3 ~ 20cm 이면 FIT
  - 하의(bottom): 허리둘레 waist_girth_cm (3cm 이상, 상한 없음)
                  엉덩이둘레 hip_girth_cm (3 ~ 15cm)              → 두 부위 모두 만족해야 FIT

입력 데이터 (서비스 플로우: 인프라 담당 기준)
  - 신체: Azure ML 응답 {"male": {예측 치수 28개}} 중 둘레 3개만 사용
          chest_girth_cm / waist_girth_cm / hip_girth_cm  → body_from_ml_response()
          ※ SAM 측정값 11개(sam_measurements)가 아니라 ML 예측값을 쓴다.
          ※ ML의 chest_width_cm 등은 '몸 너비'이며 옷 단면(chest_width)과 다른 값이다. 쓰지 않는다.
  - 옷  : 3D 의류 API(3D 담당)와 같은 데이터를 쓴다 → Azure DB fitme (fitme-sql-dev)
          garment.garments + garment.sizes + garment.measures (basis='garment')
          근거: GitHub fit-me, 브랜치 feature/3d-deploy-ml-free-test,
                garment/src/api/garments.py (조회 SQL),
                garment/src/core/garment_specs.py (chest_width·waist_width·hip_width)
          옷 치수는 '단면'(둘레의 절반)이고 한 행에 치수 하나 → sizes_from_db_rows() 로 × 2 변환, 지역 KR만.
          상품은 item_code(상품번호)로 찾는다 → MEASURES_SQL
          ※ 2026-11-15 조회 기준, 서비스 6개 상품은 아직 garment.measures 에 없고
            garment.size_musinsa_standard / size_topten / size_ziozia(이미 둘레)에만 있다.
            그 행은 × 2 없이 그대로 check_all_sizes 에 넣을 수 있다 (임시 경로).
  - 종류: category 값 '상의'/'하의'(garment.garments), 'tops'/'bottoms'(size_* 테이블) 모두 받는다.
외부 라이브러리 없이 파이썬 표준 라이브러리만 쓴다 (어디에 넣어도 의존성 추가 없음).

사용 예
  from ease_check import body_from_ml_response, sizes_from_db_rows, check_all_sizes, MEASURES_SQL
  body  = body_from_ml_response(ml_response)       # {"male": {...28개}} → 둘레 3개
  rows  = query(MEASURES_SQL, (item_code,))        # 3D 의류 API와 같은 테이블의 단면 행
  sizes = sizes_from_db_rows(rows)                 # 단면 × 2 → 둘레 (KR만)
  check_all_sizes(rows[0]["category"], body, sizes, "M")

명령줄
  py ease_check.py                     # 예시 실행
  py ease_check.py ease_request.json   # JSON 입력 → JSON 출력
"""
from __future__ import annotations

import json
import sys

RULES_VERSION = "ease-2026-11-16.v3"   # v2: 반올림 전 값으로 비교 / v3: 부위별 최대값(너무 큼) 추가
EASE_MIN_CM = 3.0   # 모든 부위 공통 최소 (팀 결정 2026-11-12)

# 부위별 여유분 허용 범위 (cm): (최소, 최대). 최대 None = 상한 없음.
# 출처 원문 위치·한계는 ML/fit_judge/SOURCES.md 에 정리돼 있다 (확인일 2026-11-10).
#
# [최소 3cm] 팀 운영값. 아래 논문의 '슬림핏' 최소 여유 범위 안에 있음을 확인함.
#   - S1 김민정·김명옥·박선경 (2014). 남성의 클래식핏과 슬림핏 셔츠 패턴 비교 분석에 관한 연구.
#        복식문화연구 22(2), 209-224. doi:10.7741/rjcc.2014.22.2.209
#        Table 4 (p.215): 슬림핏 셔츠 가슴 여유 3.5~11cm
#   - S3 김경아·홍은희·어미경 (2014). 남성 슬림 팬츠 패턴 비교 분석.
#        복식문화연구 22(4), 605-618. doi:10.7741/rjcc.2014.22.4.605
#        결론 (p.617): 20대 남성 슬림 팬츠 제안 여유 허리 2~4cm, 엉덩이 2~3cm
#
# [상의 가슴 최대 20cm] 팀 운영값 (2026-11-16). S1 Table 4 (p.215)의 클래식핏 셔츠 가슴 여유 범위
#   8~21cm 의 최대 21cm 를 기억하기 쉽게 5 단위로 내림 → 논문 범위 안의 값.
#   한계: 우직물 드레스 셔츠(면 65%·폴리 35%), 3D 가상착의 실험. 니트 티셔츠와 다를 수 있다.
#
# [하의 엉덩이 최대 15cm] 팀 운영값 (2026-11-16).
#   - S5 이효정·엄란이·이예진 (2017). 동작가동성이 향상된 작업복 하의 개발을 위한 시판 제품의 착용감 및
#        여유량 평가. 한국의류학회지 41(4), 752-770. doi:10.5850/JKSCT.2017.41.4.752
#        초록 (p.752)·Table 13 (p.769): 20대 남성 12명 착용 평가, 춘추 바지 권장 엉덩이 여유 13.6cm
#   13.6cm 를 5 단위로 올림 → 논문 값보다 1.4cm 넉넉한 값 (논문 범위 밖임을 밝혀 둔다).
#   한계: 활동성을 중시한 작업복, 표본 12명.
#
# [하의 허리 최대 없음] 팀 결정 (2026-11-16).
#   - 일반 바지의 허리 최대 여유를 정한 논문을 찾지 못함. S3의 허리 0~5.6cm (Table 2, p.609)는 슬림 팬츠 기준.
#   - 허리는 벨트로 조절할 수 있음.
#   - ML 허리둘레 예측 평균 오차 3.09cm (GitHub fit-me, feature/ml-deploy, ml/README.md)
#     가 범위 폭과 비슷해 상한을 두면 결과가 쉽게 뒤집힘.
#
# 참고: 핏별 여유량을 정한 공인 표준은 없다 (S12 Gill, S. (2011). Improving garment fit and function through
#   ease quantification. J. of Fashion Marketing and Management 15(2), 228-241. doi:10.1108/13612021111132654).
EASE_LIMITS_CM = {
    "chest_girth_cm": (EASE_MIN_CM, 20.0),
    "waist_girth_cm": (EASE_MIN_CM, None),
    "hip_girth_cm": (EASE_MIN_CM, 15.0),
}
OK, TOO_TIGHT, TOO_LOOSE = "OK", "TOO_TIGHT", "TOO_LOOSE"   # 부위별 상태

# 카테고리별로 확인할 부위: (키 이름, 한글 이름)
PARTS = {
    "top": [("chest_girth_cm", "가슴둘레")],
    "bottom": [("waist_girth_cm", "허리둘레"), ("hip_girth_cm", "엉덩이둘레")],
}

# 데이터 오류 검사용 범위 (판정 기준이 아니라 '이상한 값' 거르기)
BODY_RANGE_CM = (40.0, 200.0)       # 사람 몸 둘레로 가능한 범위
FLAT_WIDTH_RATIO = 0.65             # 옷 값이 몸의 65% 미만이면 '단면(반 둘레)'을 넣은 것으로 의심

FIT, NO_FIT, UNDETERMINED = "FIT", "NO_FIT", "UNDETERMINED"

# DB garment.measures(basis='garment')의 단면 코드 → 판정용 둘레 키, 배수
# 근거: DB 시드 ref.measure_maps (단면 × 2.00 ≈ 둘레)
DB_WIDTH_TO_GIRTH = {
    "chest_width": ("chest_girth_cm", 2.0),
    "waist_width": ("waist_girth_cm", 2.0),
    "hip_width": ("hip_girth_cm", 2.0),
}
_EPS = 1e-9   # 부동소수 오차 보정 (예: 101.1 - 98.1 = 2.99999...)

# DB garments.category 값 → 판정 종류
CATEGORY_ALIASES = {"top": "top", "bottom": "bottom", "tops": "top", "bottoms": "bottom",
                    "상의": "top", "하의": "bottom"}
DEFAULT_REGION = "KR"         # garment.sizes 의 사이즈 표기 지역. KR/US/JP 가 함께 있어 하나만 쓴다

# 기본 조회 SQL: 3D 의류 API(garments.py)와 같은 테이블·조건, 한 상품의 모든 사이즈 (판정용 단면 3종만)
MEASURES_SQL = """SELECT g.item_code, g.category, s.size_id, s.size_label, s.region,
       m.measure_code, m.basis, m.value_cm
FROM garment.garments g
JOIN garment.sizes s    ON s.garment_id = g.garment_id
JOIN garment.measures m ON m.size_id = s.size_id AND m.basis = 'garment'
WHERE g.item_code = ? AND m.measure_code IN ('chest_width', 'waist_width', 'hip_width')
ORDER BY s.region, s.size_id"""

# (임시 경로) 2026-11-15 현재 6개 상품이 들어 있는 브랜드별 테이블. 한 행 = 사이즈 하나, 값은 이미 둘레
SIZE_TABLES = {
    "MUSINSA STANDARD": "garment.size_musinsa_standard",
    "TOPTEN": "garment.size_topten",
    "ZIOZIA": "garment.size_ziozia",
}
SIZE_TABLE_SQL = ("SELECT category, product_id, size_label, chest_girth_cm, waist_girth_cm, hip_girth_cm "
                  "FROM {table} WHERE product_id = ?")
BODY_KEYS = tuple(key for parts in PARTS.values() for key, _ in parts)   # 판정에 쓰는 신체 둘레 3개


def normalize_category(category: str) -> str:
    """'tops'/'bottoms'/'상의'/'하의'/'top'/'bottom' → 'top'/'bottom'. 그 밖의 값은 ValueError."""
    c = CATEGORY_ALIASES.get(str(category).strip().lower() if category is not None else "")
    if c is None:
        raise ValueError(f"category는 'tops'/'bottoms', '상의'/'하의', 'top'/'bottom' 중 하나여야 합니다: {category!r}")
    return c


def body_from_ml_response(response: dict, gender: str = "male") -> dict:
    """Azure ML 응답에서 판정에 쓰는 둘레 3개만 꺼낸다.

    response : {"male": {"chest_girth_cm": 100.08, "waist_girth_cm": 80.56, "hip_girth_cm": 95.98, ...28개}}
               (감싸는 "male" 없이 28개가 바로 온 dict 도 받는다)
    반환     : {"chest_girth_cm": 100.08, "waist_girth_cm": 80.56, "hip_girth_cm": 95.98}
               값이 없으면 None → 판정 함수에서 UNDETERMINED
    """
    inner = response.get(gender) if isinstance(response.get(gender), dict) else response
    return {key: inner.get(key) for key in BODY_KEYS}


def sizes_from_db_rows(rows: list[dict], region: str | None = DEFAULT_REGION) -> list[dict]:
    """DB garment.measures 행 목록(3D 의류 API와 같은 데이터)을 사이즈별 둘레 dict 목록으로 바꾼다.
    ※ garment.size_* 테이블 행(이미 둘레)은 넣지 않는다 (× 2 가 두 번 됨).

    rows   : MEASURES_SQL 조회 결과 (garment.garments·sizes·measures JOIN, 한 행 = 치수 하나)
             [{"size_label": "M", "region": "KR", "measure_code": "chest_width", "basis": "garment", "value_cm": 53.0}, ...]
    region : 이 지역(region) 행만 쓴다 (기본 KR). region 컬럼이 없는 행은 그대로 쓴다.
             None 이면 거르지 않는다 (이때 같은 size_label 이 여러 지역에 있으면 값이 섞이므로 권장하지 않음).
    반환 : [{"size_label": "M", "chest_girth_cm": 106.0}, ...]  (DB에 나온 사이즈 순서 유지)

    - basis 가 'body'(권장 신체 범위)인 행은 옷 실측이 아니므로 건너뛴다.
    - 판정에 쓰지 않는 코드(총장, 소매길이 등)와 값이 없는 행은 건너뛴다.
      → 필요한 치수가 빠진 사이즈는 판정 함수에서 UNDETERMINED 가 된다.
    """
    sizes: dict[str, dict] = {}
    for r in rows:
        label = r.get("size_label")
        if label is None:
            continue
        if region is not None and r.get("region") not in (None, region):
            continue
        size = sizes.setdefault(label, {"size_label": label})
        if r.get("basis", "garment") != "garment":
            continue
        code = r.get("measure_code")
        v = _num(r.get("value_cm"))
        if code in DB_WIDTH_TO_GIRTH and v is not None:
            key, factor = DB_WIDTH_TO_GIRTH[code]
            size[key] = round(v * factor, 1)
    return list(sizes.values())


def _num(x):
    """숫자 또는 {"value":..,"lo":..,"hi":..} 형태에서 숫자를 꺼낸다. 없으면 None."""
    if isinstance(x, dict):
        x = x.get("value")
    if x is None or isinstance(x, bool):
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None   # NaN 제거


def check_ease(category: str, body: dict, garment: dict, size_label: str | None = None) -> dict:
    """한 사이즈에 대해 여유분을 계산하고 FIT / NO_FIT / UNDETERMINED를 돌려준다.

    category : "상의"/"하의" 또는 "top"/"bottom"
    body     : 예측 신체 치수 dict  {"chest_girth_cm": 98 또는 {"value": 98, "lo": .., "hi": ..}, ...}
    garment  : 선택 사이즈 실측 dict {"chest_girth_cm": 112, ...}  (둘레, cm)
    """
    category = normalize_category(category)

    parts, problems = [], []
    for key, name in PARTS[category]:
        b, g = _num(body.get(key)), _num(garment.get(key))
        lo, hi = EASE_LIMITS_CM[key]
        part = {"part": key, "name_ko": name, "body_cm": b, "garment_cm": g,
                "ease_cm": None, "ease_min_cm": lo, "ease_max_cm": hi, "status": None, "ok": None}
        if b is None or g is None:
            problems.append(f"{name} 값이 없습니다({'몸' if b is None else '옷'}).")
        elif not BODY_RANGE_CM[0] <= b <= BODY_RANGE_CM[1]:
            problems.append(f"{name} 신체 값 {b}cm가 정상 범위를 벗어났습니다.")
        elif g < b * FLAT_WIDTH_RATIO:
            problems.append(f"{name} 옷 값 {g}cm가 너무 작아 단면(반 둘레) 값으로 보입니다(sizes_from_db_rows로 둘레 변환 필요).")
        else:
            raw = g - b                                   # 비교는 반올림 전 값으로 (2.96cm → NO_FIT)
            if raw < lo - _EPS:
                status = TOO_TIGHT
            elif hi is not None and raw > hi + _EPS:      # 최대값과 같으면 FIT (20.0cm → FIT)
                status = TOO_LOOSE
            else:
                status = OK
            part["ease_cm"], part["status"], part["ok"] = round(raw, 1), status, status == OK
        parts.append(part)

    if problems:
        verdict = UNDETERMINED
        message = "판정할 수 없습니다: " + " ".join(problems)
    elif all(p["ok"] for p in parts):
        verdict = FIT
        message = "입을 수 있습니다. " + ", ".join(f"{p['name_ko']} 여유 {p['ease_cm']:+.1f}cm" for p in parts)
    else:
        verdict = NO_FIT
        reasons = []
        for p in parts:
            if p["status"] == TOO_TIGHT:
                reasons.append(f"{p['name_ko']} 여유 {p['ease_cm']:+.1f}cm로 작습니다 (기준 {p['ease_min_cm']:g}cm 미만)")
            elif p["status"] == TOO_LOOSE:
                reasons.append(f"{p['name_ko']} 여유 {p['ease_cm']:+.1f}cm로 너무 큽니다 (기준 {p['ease_max_cm']:g}cm 초과)")
        message = "맞지 않습니다. " + ", ".join(reasons)

    return {"verdict": verdict, "message_ko": message, "category": category,
            "size_label": size_label, "ease_min_cm": EASE_MIN_CM,
            "parts": parts, "rules_version": RULES_VERSION}


def check_all_sizes(category: str, body: dict, sizes: list[dict], selected_size: str | None = None) -> dict:
    """같은 상품의 모든 사이즈를 판정하고, 입을 수 있는 사이즈와 추천 사이즈를 돌려준다.

    sizes : [{"size_label": "M", "chest_girth_cm": 106}, ...]  (둘레 기준. DB 행은 sizes_from_db_rows()로 변환)
    추천 사이즈 = 입을 수 있는 사이즈 중 여유분이 가장 작은 것 (가장 몸에 가까운 사이즈)
    """
    category = normalize_category(category)
    results = [check_ease(category, body, s, s.get("size_label")) for s in sizes]
    fit = [r for r in results if r["verdict"] == FIT]
    recommended = min(fit, key=lambda r: sum(p["ease_cm"] for p in r["parts"]))["size_label"] if fit else None
    selected = next((r for r in results if r["size_label"] == selected_size), None)
    if selected_size is not None and selected is None:
        raise ValueError(f"사이즈를 찾을 수 없습니다: {selected_size!r}")
    return {"selected": selected,
            "fit_sizes": [r["size_label"] for r in fit],
            "recommended_size": recommended,
            "all_sizes": [{"size_label": r["size_label"], "verdict": r["verdict"],
                           "ease_cm": {p["part"]: p["ease_cm"] for p in r["parts"]}} for r in results],
            "rules_version": RULES_VERSION}


EXAMPLE = {
    "category": "상의",
    "selected_size": "M",
    "body": {"chest_girth_cm": {"value": 98.0, "lo": 95.8, "hi": 100.2}},
    "sizes": [
        {"size_label": "S", "chest_girth_cm": 100.0},
        {"size_label": "M", "chest_girth_cm": 106.0},
        {"size_label": "L", "chest_girth_cm": 112.0},
    ],
}


def main(argv: list[str]) -> int:
    req = EXAMPLE
    if len(argv) > 1:
        with open(argv[1], encoding="utf-8") as f:
            req = json.load(f)
    # 신체: "ml_response"(ML 응답 그대로)가 있으면 둘레 3개를 꺼내고, 없으면 "body" 사용
    body = body_from_ml_response(req["ml_response"]) if "ml_response" in req else req["body"]
    # 옷: "db_rows"(DB 단면 행)가 있으면 둘레로 변환, 없으면 "sizes"(이미 둘레)를 그대로 사용
    sizes = (sizes_from_db_rows(req["db_rows"], req.get("region", DEFAULT_REGION))
             if "db_rows" in req else req["sizes"])
    out = check_all_sizes(req["category"], body, sizes, req.get("selected_size"))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
