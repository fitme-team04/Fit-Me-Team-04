# ease_check - 상의 가슴 여유분 착용 판정

**상의만** 판정한다. 옷 가슴둘레 − 몸 가슴둘레(여유분)가 **3~20cm**이면 맞음(FIT)이다.
(팀 결정: 최소 2026-11-12, 최대 2026-11-16, 하의 제외 2026-11-16 / 기준 버전 `ease-2026-11-16.v4`)

> **하의 제외 (2026-11-16 팀 결정):** 하의는 시간이 부족해 3D에서 빠졌다. 그래서 여유분 판정도 상의만 한다.
> `category`에 `하의`/`bottoms`/`bottom`을 넣으면 `ValueError`("하의는 판정하지 않습니다")가 난다.

---

## 1. 파일 구성

모든 파일이 한 폴더(`ease_check/`)에 있다.

| 파일 | 내용 |
|---|---|
| `ease_check.py` | 판정 코드 + ML 응답·DB 행 변환 함수 + 조회 SQL (파이썬 표준 라이브러리만 사용, 추가 설치 없음) |
| `test_ease_check.py` | 테스트 29개 |
| `ease_request.json` | 입력 예시 (Azure DB 실제 값: UNIQLO 크루넥T `E422992-000`) |
| `EASE_CHECK_README.md` | 이 문서 |

---

## 2. 판정 규칙

- 여유분 = 옷 가슴**둘레** − 몸 가슴**둘레** (cm)
- **3cm ≤ 여유분 ≤ 20cm**이면 FIT

| 결과 | 조건 | `status` | 화면 문구 예 |
|---|---|---|---|
| `FIT` | 3 ~ 20cm | `OK` | "입을 수 있습니다. 가슴둘레 여유 +5.9cm" |
| `NO_FIT` | 3cm 미만 | `TOO_TIGHT` | "맞지 않습니다. 가슴둘레 여유 -0.1cm로 작습니다 (기준 3cm 미만)" |
| `NO_FIT` | 20cm 초과 | `TOO_LOOSE` | "맞지 않습니다. 가슴둘레 여유 +27.9cm로 너무 큽니다 (기준 20cm 초과)" |
| `UNDETERMINED` | 치수 없음 / 숫자 아님 / 비정상 값 / 단면값 의심 | (없음) | "판정할 수 없습니다: …" |

- 비교는 **반올림 전 값**으로 한다. 실제 여유 2.96cm는 화면에 `+3.0cm`로 보이지만 `TOO_TIGHT`이다.
  3cm·20cm와 **같은 값은 FIT**이다 (+20.0cm → FIT, +20.1cm → `TOO_LOOSE`). 부동소수 오차(101.1 − 98.1 = 2.9999…)만 보정한다.
- 추천 사이즈 = FIT인 사이즈 중 여유분이 가장 작은 것 (작거나 너무 큰 사이즈는 추천하지 않음)
- 데이터가 없을 때 임의로 FIT을 내지 않도록 `UNDETERMINED`를 둔다.
- 기준을 바꾸면 `ease_check.py`의 `EASE_LIMITS_CM`과 `RULES_VERSION`을 함께 수정한다.
- 데이터 오류 검사용 범위(판정 기준 아님): 신체 둘레 40~200cm, 옷 값이 몸의 65% 미만이면 단면값 의심.
- ML 가슴둘레 예측 평균 오차가 2.41cm라서, 여유분이 3cm·20cm 근처면 실제와 다를 수 있다.

### 2-1. 기준값의 근거

**3cm·20cm는 공인 표준이 아니라 "논문 범위를 참고한 팀 운영값"이다.**
- ISO 8559-1:2017, KS K 0050은 신체 측정 정의·호칭만 다루고 **핏별 여유량(cm)은 정하지 않는다.**
- S12 Gill (2011)도 "여유량 지침은 많지만 그 수치를 정한 근거는 거의 제시되지 않는다"고 지적한다.
- 원문 위치·한계 전체 목록: `ML/fit_judge/SOURCES.md` (확인일 2026-11-10)

| ID | 출처 (저자, 연도, 학술지, DOI) | 우리가 쓴 값 | 원문 위치 | 표본·방식 | 한계 |
|---|---|---|---|---|---|
| S1 | 김민정·김명옥·박선경 (2014). 남성의 클래식핏과 슬림핏 셔츠 패턴 비교 분석에 관한 연구 — 3D 가상착의를 활용하여. *복식문화연구* 22(2), 209–224. [doi:10.7741/rjcc.2014.22.2.209](https://doi.org/10.7741/rjcc.2014.22.2.209) | 가슴 여유 슬림 3.5~11cm, 클래식 8~21cm → **최소 3cm(슬림 최소 근처), 최대 20cm(클래식 최대 21cm를 5 단위로 내림)** | Table 4 (p.215), 결론 (p.222) | 3D 가상착의 실험 (평가자 수는 원문 재확인 필요) | 우직물 드레스 셔츠라 니트 티셔츠와 다를 수 있음 |
| S12 | Gill, S. (2011). Improving garment fit and function through ease quantification. *Journal of Fashion Marketing and Management* 15(2), 228–241. [doi:10.1108/13612021111132654](https://doi.org/10.1108/13612021111132654) | 공인 여유량 표준이 없다는 근거 | 초록 | 문헌 검토 | — |
| ML | GitHub `fit-me`, 브랜치 `feature/ml-deploy`, `ml/README.md` | 가슴둘레 예측 평균 오차 2.41cm | 성능 표 | 사이즈코리아 남성 시험 613명 | 줄자 실측 학습, 실제 사진 오차는 더 클 수 있음 |

**왜 이 학술지인가:** *복식문화연구*(한국복식문화학회)는 심사를 거치는 국내 의류학 학술지이고, **한국 남성 상의**의 가슴 여유량을 cm로 제시한 연구라서 골랐다. DOI로 원문을 확인할 수 있다.

**신뢰 한계:** 3D 가상착의 실험이고 드레스 셔츠 연구다. 그래서 기준값은 "검증된 표준"이 아니라 "출발점"이며, 팀원 실제 옷 실측 등으로 확인해 조정한다.

---

## 3. 입력 데이터

### 3-1. 신체: Azure ML 응답 (`male` 객체, 예측 치수 28개)

- ML 응답 `{"male": {예측 치수 28개}}` 중 **`chest_girth_cm`(가슴둘레)만** 쓴다 → `body_from_ml_response()`
- **SAM 측정값 11개(`sam_measurements`)가 아니라 ML 예측값을 쓴다.** SAM 11개에는 가슴둘레가 없다.
- ML의 `chest_width_cm`는 **몸 가슴너비**(약 35cm)다. 옷 가슴단면(`chest_width`, 약 53cm)과 이름이 비슷하지만 **다른 값이므로 쓰지 않는다.**
- 감싸는 `"male"` 없이 28개가 바로 온 dict도 받는다.

### 3-2. 옷: 3D 의류 API(3D 담당)와 같은 데이터

**3D 화면의 옷 크기와 판정 결과가 같은 숫자에서 나오도록, 3D 의류 API가 쓰는 테이블을 그대로 쓴다.**

- 위치: Azure SQL 서버 `fitme-sql-dev` > DB `fitme` > `garment.garments` + `garment.sizes` + `garment.measures` (`basis='garment'`, `measure_code='chest_width'`)
- 근거 (개발용 비공개 레포, 브랜치 `feature/3d-deploy-ml-free-test`):
  - `garment/src/api/garments.py` — 위 3개 테이블을 `item_code`·`size_id`로 조회
  - `garment/src/core/garment_specs.py` — 상의(crewneck) `chest_width`(가슴단면)
- 옷 가슴은 **단면(둘레의 절반)**이고 한 행에 치수 하나 → `sizes_from_db_rows()`로 **× 2** 해서 둘레로 바꾼다.
  - × 2 근거: Azure DB `fitme` > `ref.measure_maps` (`chest_girth` ↔ `chest_width`, factor 2.00)
- **지역(`region`)은 `KR`만** 쓴다. 같은 상품에 KR·US 사이즈가 함께 있다 (예: 크루넥T `E422992-000`은 KR M 53cm, US M 56cm).
- `basis='body'` 행, 다른 치수(`body_length` 등), 값이 없는 행은 건너뛴다. 3D API 조회 결과처럼 `basis` 열이 없는 행도 받는다.

조회 SQL (`ease_check.py`의 `MEASURES_SQL`):

```sql
SELECT g.item_code, g.category, s.size_id, s.size_label, s.region,
       m.measure_code, m.basis, m.value_cm
FROM garment.garments g
JOIN garment.sizes s    ON s.garment_id = g.garment_id
JOIN garment.measures m ON m.size_id = s.size_id AND m.basis = 'garment'
WHERE g.item_code = ? AND m.measure_code = 'chest_width'
ORDER BY s.region, s.size_id;
```

**2026-11-16 Azure DB 기준, 가슴단면(`chest_width`)이 있는 상의:** UNIQLO 상의 여러 개, COVERNAT `1848166`.
남성이 입을 수 있는 KR 사이즈 상품은 UNIQLO 크루넥T `E422992-000`(공용), UNIQLO 드라이컬러크루넥T `E465187-000`(남성), COVERNAT `1848166`(공용)이다.

### 3-3. 종류: `category`

`상의`(`garment.garments.category`), `tops`, `top`만 받는다. 하의는 `ValueError`.

---

## 4. 함수

| 함수·상수 | 하는 일 |
|---|---|
| `body_from_ml_response(response, gender="male")` | ML 응답 → `{"chest_girth_cm": ...}` |
| `MEASURES_SQL` | 3D 의류 API와 같은 테이블에서 한 상품의 가슴단면 행을 가져오는 SQL (`item_code`로 조회) |
| `sizes_from_db_rows(rows, region="KR")` | 가슴단면 행 → 사이즈별 가슴둘레 |
| `check_ease(category, body, garment, size_label=None)` | 한 사이즈를 판정 |
| `check_all_sizes(category, body, sizes, selected_size=None)` | 같은 상품의 모든 사이즈를 판정하고 `fit_sizes`(맞는 사이즈 목록), `recommended_size`(추천)를 돌려줌 |

### 호출 예

```python
from ease_check import body_from_ml_response, sizes_from_db_rows, check_all_sizes, MEASURES_SQL

body   = body_from_ml_response(ml_response)       # {"male": {...28개}} → 가슴둘레
rows   = query(MEASURES_SQL, (item_code,))        # 예: 'E422992-000'
sizes  = sizes_from_db_rows(rows)                 # 가슴단면 × 2 → 가슴둘레 (KR만)
result = check_all_sizes(rows[0]["category"], body, sizes, selected_size="M")
```

### 입력 예 (`ease_request.json`)

Azure DB 실제 값(UNIQLO 크루넥T `E422992-000`)이다. `ml_response`는 ML 응답 그대로 넣으면 가슴둘레만 꺼낸다.

```json
{
  "category": "상의",
  "selected_size": "M",
  "ml_response": {"male": {"chest_girth_cm": 100.08, "...": "28개"}},
  "db_rows": [
    {"item_code": "E422992-000", "category": "상의", "size_label": "M", "region": "KR",
     "measure_code": "chest_width", "basis": "garment", "value_cm": 53.0},
    "... KR XS~4XL 8개 + US M 1개(제외됨)"
  ]
}
```

### 출력 예 (가슴 100.08cm)

```json
{
  "selected": {
    "verdict": "FIT",
    "message_ko": "입을 수 있습니다. 가슴둘레 여유 +5.9cm",
    "category": "top",
    "size_label": "M",
    "parts": [{"part": "chest_girth_cm", "name_ko": "가슴둘레", "body_cm": 100.08, "garment_cm": 106.0,
               "ease_cm": 5.9, "ease_min_cm": 3.0, "ease_max_cm": 20.0, "status": "OK", "ok": true}],
    "rules_version": "ease-2026-11-16.v4"
  },
  "fit_sizes": ["M", "L", "XL"],
  "recommended_size": "M",
  "all_sizes": [
    {"size_label": "S",   "verdict": "NO_FIT", "ease_cm": {"chest_girth_cm": -0.1}, "status": {"chest_girth_cm": "TOO_TIGHT"}},
    {"size_label": "M",   "verdict": "FIT",    "ease_cm": {"chest_girth_cm": 5.9},  "status": {"chest_girth_cm": "OK"}},
    {"size_label": "XXL", "verdict": "NO_FIT", "ease_cm": {"chest_girth_cm": 27.9}, "status": {"chest_girth_cm": "TOO_LOOSE"}},
    "..."
  ],
  "rules_version": "ease-2026-11-16.v4"
}
```

| 사이즈 (KR) | 옷 가슴둘레 | 여유분 | 결과 |
|---|---|---|---|
| XS | 94 | −6.1 | 작음 |
| S | 100 | −0.1 | 작음 |
| **M** | 106 | +5.9 | **FIT (추천)** |
| L | 112 | +11.9 | FIT |
| XL | 120 | +19.9 | FIT |
| XXL | 128 | +27.9 | 너무 큼 |
| 3XL | 136 | +35.9 | 너무 큼 |
| 4XL | 144 | +43.9 | 너무 큼 |

---

## 5. 실행 방법 (PowerShell)

1. 터미널에서 `ease_check` 폴더로 이동 (경로에 띄어쓰기가 있으면 **큰따옴표 필수**)
   ```powershell
   cd "<ease_check 폴더 경로>"
   ```
2. 한글 깨짐 방지 (창을 새로 열 때마다)
   ```powershell
   $env:PYTHONIOENCODING="utf-8"
   ```
3. 내장 예시 실행 → M FIT, 추천 M
   ```powershell
   py ease_check.py
   ```
4. JSON 파일로 실행 → UNIQLO 크루넥T M FIT(+5.9cm), 맞는 사이즈 M·L·XL, 추천 M
   ```powershell
   py ease_check.py ease_request.json
   ```
5. 테스트 → `29 passed`가 나오면 정상
   ```powershell
   py -m pytest test_ease_check.py -q
   ```
   `No module named pytest`가 나오면 먼저 `py -m pip install pytest`

### 자주 나는 오류

| 메시지 | 원인 | 해결 |
|---|---|---|
| `can't open file ... ease_check.py` | 다른 폴더에서 실행함 | 1번 다시 (큰따옴표 포함) |
| `py : ... 인식되지 않습니다` | 파이썬 실행기가 PATH에 없음 | `py` 대신 `python` |
| 한글이 `����`로 표시 | 콘솔 인코딩 | 2번 실행 |
| `하의는 판정하지 않습니다` | category에 하의를 넣음 | 상의만 지원 (2026-11-16 팀 결정) |
| 결과가 전부 `UNDETERMINED` | 가슴단면을 × 2 없이 넣음 / ML 몸 너비 키를 넣음 | `sizes_from_db_rows()`, `body_from_ml_response()` 사용 |
| `사이즈를 찾을 수 없습니다` | 고른 사이즈가 KR 행에 없음 | `garment.sizes`의 `region` 확인 |

---

## 6. 테스트 파일 설명 (`test_ease_check.py`, 29개)

| 테스트 | 확인 내용 |
|---|---|
| `test_exactly_3cm_is_fit` | 여유 정확히 3.0cm → FIT |
| `test_under_3cm_is_too_tight` | 2.9cm → NO_FIT, `TOO_TIGHT`, "작습니다" |
| `test_rounding_does_not_turn_2_96_into_fit` | 2.96cm → 표시는 3.0이지만 NO_FIT |
| `test_float_error_at_exactly_3cm_is_fit` | 101.1 − 98.1 같은 부동소수 오차에도 3.0 → FIT |
| `test_exactly_20cm_is_fit` | 정확히 20cm → FIT |
| `test_over_20cm_is_too_loose` | 20.1cm → NO_FIT, `TOO_LOOSE`, "너무 큽니다" |
| `test_bad_data_is_undetermined` (5건) | 몸 값 없음 / 옷 값 없음 / 단면값 / 비정상 신체값 / 숫자 아님 → UNDETERMINED |
| `test_top_category_is_accepted` (4건) | `상의`/`tops`/`top`/`TOP` 허용 |
| `test_bottom_category_is_rejected` (3건) | `하의`/`bottoms`/`bottom` → ValueError |
| `test_unknown_category_raises` | `아우터` → ValueError |
| `test_ml_response_keeps_only_chest_girth` | ML 응답에서 가슴둘레만 꺼냄 |
| `test_ml_response_without_male_wrapper` | `"male"` 없이 온 응답도 처리 |
| `test_ml_response_missing_chest_is_undetermined` | 가슴둘레가 없으면 UNDETERMINED |
| `test_db_width_is_doubled_and_kr_only` | 가슴단면 × 2, KR만 사용 (US M 제외) |
| `test_db_rows_skip_body_basis_and_other_codes` | body 행·총장 행은 건너뜀 |
| `test_db_row_without_basis_key` | 3D API 조회 결과 형식(`basis` 없음)도 처리 |
| `test_measures_sql_matches_3d_api_tables` | `MEASURES_SQL`이 3D API와 같은 테이블·조건 |
| `test_uniqlo_end_to_end` | UNIQLO 크루넥T 실제 값 → M FIT, 맞는 사이즈 M·L·XL, 추천 M |
| `test_no_fit_size_gives_no_recommendation` | 맞는 사이즈가 없으면 추천 없음 |
| `test_unknown_size_raises` | 없는 사이즈 → ValueError |

### `# noqa: E402`란?

```python
sys.path.insert(0, str(Path(__file__).resolve().parent))   # ① 이 파일이 있는 폴더를 경로에 추가
from ease_check import (...)  # noqa: E402                  # ② 그다음 import
```

- 실행에는 영향 없는 주석. 코드 검사 도구(flake8 등)에 "이 줄은 경고하지 마"라고 알리는 표시.
- `E402` = "import가 파일 맨 위에 있지 않음" 경고 번호. ①을 먼저 해야 ②가 되므로 의도한 순서다.

---

## 7. 서비스 플로우 연결 (인프라 담당 플로우 기준)

```
3-2. [워커] Redis 큐에서 작업을 꺼내 동시에 보냄
       ├─ 신체 API: 사진·키·몸무게 → SAM 11개 → Azure ML → 예측 28개({"male": {...}})
       └─ 의류 API: item_code·size_id → garment.garments·sizes·measures 조회 → Blender → 상의 GLB
★ [워커] 두 결과를 받으면 ease_check 실행 (1초 미만, CPU)
       body  = body_from_ml_response(신체 API가 넘겨준 ML 응답)
       sizes = sizes_from_db_rows(MEASURES_SQL 조회 결과)   ← 의류 API와 같은 테이블
       check_all_sizes("상의", body, sizes, 선택 사이즈)
5-2. [웹앱] 모델 링크와 함께 판정 결과를 Redis에 보관 → 브라우저에 전달
5-4. [브라우저] 3D 착장 화면 옆에 판정 결과·가슴 여유분·추천 사이즈 표시
```

| 파트 | 할 일 |
|---|---|
| ML (나) | `ease_check.py`와 입출력 예시 전달. 기준을 바꾸면 `RULES_VERSION` 올림 |
| ML 신체 예측 | `male` 객체에 `chest_girth_cm` 유지 (이름·둘레 기준) |
| 3D 신체 API | 워커 응답에 ML 예측 치수(최소 `chest_girth_cm`) 포함 |
| 웹앱·워커 | `MEASURES_SQL` 조회 + `check_all_sizes()` 호출, 결과를 Redis에 보관 |
| 프론트 | `verdict`, `message_ko`, 가슴 여유분, `status`(작음/너무 큼), `recommended_size` 표시. 판정 숫자를 프론트에 따로 두지 않음 |

### 전달 형식

| 전달물 | 형식 | 이유 |
|---|---|---|
| 코드 | `.py` 파일 1개 | 표준 라이브러리만 써서 웹앱 폴더에 복사 후 `import`만 하면 됨 |
| 입출력 약속 | `.json` 예시 | ML·3D·웹앱이 같은 키 이름으로 맞출 수 있음 |
| 검증 근거 | 테스트 파일 | 받은 쪽에서 `pytest`로 "3cm·20cm 경계 / 단면 변환 / ML 응답"을 바로 확인 |
