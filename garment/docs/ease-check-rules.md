# ease_check - 여유분 3cm 기준 착용 판정

슬림/스탠다드/오버핏 구분 없이, **여유분(옷 둘레 − 몸 둘레)만으로** "입을 수 있다 / 못 입는다"를 판정하는 모듈이다.
(팀 결정: 최소 2026-11-12, 최대 2026-11-16 / 기준 버전 `ease-2026-11-16.v3`)

---

## 1. 파일 구성

모든 파일이 한 폴더(`ease_check/`)에 있다.

| 파일 | 내용 |
|---|---|
| `ease_check.py` | 판정 코드 + ML 응답·DB 행 변환 함수 + 조회 SQL (파이썬 표준 라이브러리만 사용, 추가 설치 없음) |
| `test_ease_check.py` | 테스트 38개 |
| `ease_request.json` | 입력 예시 (하의, ML 응답 + 3D 의류 API와 같은 DB 행 형식) |
| `EASE_CHECK_README.md` | 이 문서 |

---

## 2. 판정 규칙

- 여유분 = 옷 실측 **둘레** − 몸 **둘레** (cm)
- 부위마다 **최소 ≤ 여유분 ≤ 최대**이면 맞음

| 판정 부위 | 최소 | 최대 | 근거 요약 (자세히는 2-1) |
|---|---|---|---|
| 상의 가슴둘레 `chest_girth_cm` | 3cm | **20cm** | S1 클래식핏 셔츠 가슴 여유 8~21cm의 최대 21cm → 5 단위로 내림 |
| 하의 허리둘레 `waist_girth_cm` | 3cm | **없음** | 일반 바지 허리 최대 근거 없음, 벨트로 조절, ML 허리 오차 3.09cm |
| 하의 엉덩이둘레 `hip_girth_cm` | 3cm | **15cm** | S5 바지 권장 엉덩이 여유 13.6cm → 5 단위로 올림 |

하의는 허리·엉덩이 **두 부위 모두** 범위 안이어야 FIT이다.

| 결과 | 조건 | 부위 `status` | 화면 문구 예 |
|---|---|---|---|
| `FIT` | 모든 부위가 범위 안 | `OK` | "입을 수 있습니다. 가슴둘레 여유 +8.0cm" |
| `NO_FIT` | 한 부위라도 최소 미만 | `TOO_TIGHT` | "맞지 않습니다. 허리둘레 여유 +0.6cm로 작습니다 (기준 3cm 미만)" |
| `NO_FIT` | 한 부위라도 최대 초과 | `TOO_LOOSE` | "맞지 않습니다. 가슴둘레 여유 +27.0cm로 너무 큽니다 (기준 20cm 초과)" |
| `UNDETERMINED` | 치수 없음 / 숫자 아님 / 비정상 값 / 단면값 의심 | (없음) | "판정할 수 없습니다: …" |

- 비교는 **반올림 전 값**으로 한다. 실제 여유 2.96cm는 화면에 `+3.0cm`로 보이지만 `TOO_TIGHT`이다.
  최소·최대와 **같은 값은 FIT**이다 (가슴 +20.0cm → FIT, +20.1cm → `TOO_LOOSE`). 부동소수 오차(101.1 − 98.1 = 2.9999…)만 보정한다.
- 추천 사이즈는 FIT인 사이즈 중 여유분이 가장 작은 것이다. 너무 큰 사이즈는 추천하지 않는다.
- 데이터가 없을 때 임의로 FIT을 내지 않도록 `UNDETERMINED`를 둔다.
- 기준을 바꾸면 `ease_check.py`의 `EASE_LIMITS_CM`과 `RULES_VERSION`을 함께 수정한다.
- 데이터 오류 검사용 범위(판정 기준 아님): 신체 둘레 40~200cm, 옷 값이 몸의 65% 미만이면 단면값 의심.
- 주의: 고무줄 허리 하의는 허리 여유가 3cm 미만이어도 실제로는 입을 수 있지만, 현재 규칙은 NO_FIT으로 판정한다.

### 2-1. 기준값의 근거

**모든 기준값은 공인 표준이 아니라 "논문 범위를 참고한 팀 운영값"이다.**
- ISO 8559-1:2017, KS K 0050은 신체 측정 정의·호칭만 다루고 **핏별 여유량(cm)은 정하지 않는다.**
- S12 Gill (2011)도 "여유량 지침은 많지만 그 수치를 정한 근거는 거의 제시되지 않는다"고 지적한다.
- 원문 위치·한계 전체 목록: `ML/fit_judge/SOURCES.md` (확인일 2026-11-10)

| ID | 출처 (저자, 연도, 학술지, DOI) | 우리가 쓴 값 | 원문 위치 | 표본·방식 | 한계 |
|---|---|---|---|---|---|
| S1 | 김민정·김명옥·박선경 (2014). 남성의 클래식핏과 슬림핏 셔츠 패턴 비교 분석에 관한 연구 — 3D 가상착의를 활용하여. *복식문화연구* 22(2), 209–224. [doi:10.7741/rjcc.2014.22.2.209](https://doi.org/10.7741/rjcc.2014.22.2.209) | 가슴 여유 슬림 3.5~11cm, 클래식 8~21cm → **최소 3cm 확인, 최대 20cm** | Table 4 (p.215), 결론 (p.222) | 3D 가상착의 실험 (평가자 수는 원문 재확인 필요) | 우직물 드레스 셔츠라 니트 티셔츠와 다를 수 있음 |
| S3 | 김경아·홍은희·어미경 (2014). 남성 슬림 팬츠 패턴 비교 분석 — 3D CLO 가상착의 시스템을 활용하여. *복식문화연구* 22(4), 605–618. [doi:10.7741/rjcc.2014.22.4.605](https://doi.org/10.7741/rjcc.2014.22.4.605) | 슬림 팬츠 허리 2~4cm, 엉덩이 2~3cm → **최소 3cm 확인**. 허리 0~5.6cm는 슬림 한정이라 허리 최대에는 안 씀 | Table 2 (p.609), 결론 (p.617) | 3D 가상착의 (사람 착용 아님) | 슬림 팬츠 한정 |
| S5 | 이효정·엄란이·이예진 (2017). 동작가동성이 향상된 작업복 하의 개발을 위한 시판 제품의 착용감 및 여유량 평가. *한국의류학회지* 41(4), 752–770. [doi:10.5850/JKSCT.2017.41.4.752](https://doi.org/10.5850/JKSCT.2017.41.4.752) | 춘추 바지 권장 엉덩이 여유 13.6cm → **최대 15cm** (1.4cm 올림, 논문 값보다 넉넉함) | 초록 (p.752), Table 13 (p.769) | 20대 남성 12명 착용 평가 | 활동성 중시 작업복, 표본 작음 |
| S12 | Gill, S. (2011). Improving garment fit and function through ease quantification. *Journal of Fashion Marketing and Management* 15(2), 228–241. [doi:10.1108/13612021111132654](https://doi.org/10.1108/13612021111132654) | 공인 여유량 표준이 없다는 근거 | 초록 | 문헌 검토 | — |
| ML | GitHub `fit-me`, 브랜치 `feature/ml-deploy`, `ml/README.md` | 허리둘레 예측 평균 오차 3.09cm, 가슴둘레 2.41cm → **허리 상한을 두지 않는 근거** | 성능 표 | 사이즈코리아 남성 시험 613명 | 줄자 실측 학습, 실제 사진 오차는 더 클 수 있음 |

**왜 이 학술지인가:** *복식문화연구*(한국복식문화학회), *한국의류학회지*(한국의류학회)는 심사를 거치는 국내 의류학 학술지이고, **한국 남성 체형**을 대상으로 여유량을 cm로 제시한 연구라서 골랐다. 모든 논문은 DOI로 원문을 확인할 수 있다.

**신뢰 한계:** 표본이 작거나(12명) 3D 가상착의 실험이다. 그래서 기준값은 "검증된 표준"이 아니라 "출발점"이며, 팀원 실제 옷 실측 등으로 확인해 조정한다.

---

## 3. 입력 데이터

### 3-1. 신체: Azure ML 응답 (`male` 객체, 예측 치수 28개)

ML 응답 `{"male": {예측 치수 28개}}` 중 **둘레 3개만** 쓴다 → `body_from_ml_response()`

| 쓰는 키 | 뜻 |
|---|---|
| `chest_girth_cm` | 가슴둘레 |
| `waist_girth_cm` | 허리둘레 |
| `hip_girth_cm` | 엉덩이둘레 |

- **SAM 측정값 11개(`sam_measurements`)가 아니라 ML 예측값을 쓴다.** SAM 11개에는 가슴·허리둘레가 없다.
- ML의 `chest_width_cm`, `waist_width_cm`, `hip_width_cm`는 **몸 너비**(가슴너비 약 35cm)다. 옷 단면(`chest_width`, 약 53cm)과 이름이 비슷하지만 **다른 값이므로 쓰지 않는다.**
- 감싸는 `"male"` 없이 28개가 바로 온 dict도 받는다.

### 3-2. 옷: 3D 의류 API(3D 담당)와 같은 데이터

**3D 화면의 옷 크기와 판정 결과가 같은 숫자에서 나오도록, 3D 의류 API가 쓰는 테이블을 그대로 쓴다.**

- 위치: Azure SQL 서버 `fitme-sql-dev` > DB `fitme` > `garment.garments` + `garment.sizes` + `garment.measures` (`basis='garment'`)
- 근거 (개발용 비공개 레포, 브랜치 `feature/3d-deploy-ml-free-test`):
  - `garment/src/api/garments.py` — 위 3개 테이블을 `item_code`·`size_id`로 조회
  - `garment/src/core/garment_specs.py` — 상의 `chest_width`, 하의 `waist_width`·`hip_width` (단면)
  - `garment/src/core/catalog_mapping.py` — `category` `상의`/`하의`
  - `db/azure/3d/README.md` — "상품·실측은 기존 garment.garments/sizes/measures를 재사용"

옷 치수는 **단면(옷을 펼친 너비 = 둘레의 절반)**이고 **한 행에 치수 하나**다 → `sizes_from_db_rows()`로 × 2 해서 둘레로 바꾼다.

| `measure_code` (basis=`garment`) | 판정용 키 | 변환 |
|---|---|---|
| `chest_width` (가슴단면) | `chest_girth_cm` | × 2 |
| `waist_width` (허리단면) | `waist_girth_cm` | × 2 |
| `hip_width` (엉덩이단면) | `hip_girth_cm` | × 2 |

- × 2 근거: Azure DB `fitme` > `ref.measure_maps` (`chest_girth` ↔ `chest_width`, factor 2.00 등)
- **지역(`region`)은 기본 `KR`만 쓴다.** `garment.sizes`에 KR/US/JP가 섞여 있어(2026-11-15: JP 99, KR 43, US 47행) 같은 라벨의 값이 섞이지 않게 한다.
- `basis = 'body'`(권장 신체 범위) 행, 판정에 쓰지 않는 코드(`body_length` 등), 값이 없는 행은 건너뛴다. 3D API 조회 결과처럼 `basis` 열이 없는 행도 받는다.

조회 SQL (`ease_check.py`의 `MEASURES_SQL`, 한 상품의 모든 사이즈):

```sql
SELECT g.item_code, g.category, s.size_id, s.size_label, s.region,
       m.measure_code, m.basis, m.value_cm
FROM garment.garments g
JOIN garment.sizes s    ON s.garment_id = g.garment_id
JOIN garment.measures m ON m.size_id = s.size_id AND m.basis = 'garment'
WHERE g.item_code = ? AND m.measure_code IN ('chest_width', 'waist_width', 'hip_width')
ORDER BY s.region, s.size_id;
```

> **현재 상태 (2026-11-15 Azure DB 조회)**
> - 서비스 6개 상품(무신사 스탠다드·탑텐·지오지아 상하의)은 **아직 `garment.garments`·`measures`에 없다.**
>   지금은 `garment.size_musinsa_standard` / `garment.size_topten` / `garment.size_ziozia`에만 있다 (값은 이미 둘레, `category` `tops`/`bottoms`).
> - `garment.measures`에는 `waist_width`·`hip_width` 행이 없다 (하의 데이터 없음).
> - 6개 상품이 `garment.measures`에 들어오기 전까지는 `size_*` 행을 **× 2 없이 그대로** `check_all_sizes()`에 넣어 쓸 수 있다 (임시 경로).

### 3-3. 종류: `category`

`상의`/`하의`(`garment.garments`), `tops`/`bottoms`(`size_*` 테이블), `top`/`bottom` 모두 받는다. 그 밖의 값은 `ValueError`.

---

## 4. 함수

| 함수·상수 | 하는 일 |
|---|---|
| `body_from_ml_response(response, gender="male")` | ML 응답 → 판정용 신체 둘레 3개 |
| `MEASURES_SQL` | 3D 의류 API와 같은 테이블에서 한 상품의 단면 행을 가져오는 SQL (`item_code`로 조회) |
| `sizes_from_db_rows(rows, region="KR")` | 단면 행 → 사이즈별 둘레 |
| `check_ease(category, body, garment, size_label=None)` | 한 사이즈를 판정 |
| `check_all_sizes(category, body, sizes, selected_size=None)` | 같은 상품의 모든 사이즈를 판정하고, 입을 수 있는 사이즈 목록 `fit_sizes`와 추천 사이즈 `recommended_size`(입을 수 있는 것 중 가장 몸에 가까운 것)를 돌려줌 |

- `body` 값은 숫자(`98`) 또는 범위(`{"value": 98, "lo": .., "hi": ..}`) 둘 다 가능. 판정에는 `value`만 사용.
- 없는 사이즈를 `selected_size`로 주면 `ValueError`.

### 호출 예

```python
from ease_check import body_from_ml_response, sizes_from_db_rows, check_all_sizes, MEASURES_SQL

body   = body_from_ml_response(ml_response)       # {"male": {...28개}} → 둘레 3개
rows   = query(MEASURES_SQL, (item_code,))        # 3D 의류 API와 같은 테이블의 단면 행
sizes  = sizes_from_db_rows(rows)                 # 단면 × 2 → 둘레 (KR만)
result = check_all_sizes(rows[0]["category"], body, sizes, selected_size="M")
```

### 입력 예 (`ease_request.json`)

`ml_response`(ML 응답 그대로)와 `db_rows`(`MEASURES_SQL` 조회 결과 형식)를 주면 자동으로 변환한다.
`value_cm`은 **단면 예시값**이다 (6개 상품이 아직 `garment.measures`에 없어서).

```json
{
  "category": "하의",
  "selected_size": "M(31)",
  "region": "KR",
  "ml_response": {"male": {"waist_girth_cm": 82.0, "hip_girth_cm": 96.0, "chest_girth_cm": 100.1, "...": "28개"}},
  "db_rows": [
    {"item_code": "MSG3PP1401BK", "category": "하의", "size_label": "M(31)", "region": "KR", "measure_code": "waist_width", "basis": "garment", "value_cm": 41.3},
    {"item_code": "MSG3PP1401BK", "category": "하의", "size_label": "M(31)", "region": "KR", "measure_code": "hip_width",   "basis": "garment", "value_cm": 50.3},
    {"item_code": "MSG3PP1401BK", "category": "하의", "size_label": "L(32)", "region": "KR", "measure_code": "waist_width", "basis": "garment", "value_cm": 42.5},
    {"item_code": "MSG3PP1401BK", "category": "하의", "size_label": "L(32)", "region": "KR", "measure_code": "hip_width",   "basis": "garment", "value_cm": 51.5}
  ]
}
```
(실제 파일에는 건너뛰는 예시 — ML의 몸 너비 키, US 지역 행 — 도 들어 있다)

### 출력 예 (요약)

```json
{
  "selected": {
    "verdict": "NO_FIT",
    "message_ko": "맞지 않습니다. 허리둘레 여유 +0.6cm로 작습니다 (기준 3cm 미만)",
    "category": "bottom",
    "parts": [
      {"part": "waist_girth_cm", "body_cm": 82.0, "garment_cm": 82.6, "ease_cm": 0.6,
       "ease_min_cm": 3.0, "ease_max_cm": null, "status": "TOO_TIGHT", "ok": false},
      {"part": "hip_girth_cm",   "body_cm": 96.0, "garment_cm": 100.6, "ease_cm": 4.6,
       "ease_min_cm": 3.0, "ease_max_cm": 15.0, "status": "OK", "ok": true}
    ],
    "rules_version": "ease-2026-11-16.v3"
  },
  "fit_sizes": ["L(32)"],
  "recommended_size": "L(32)",
  "all_sizes": [ ... ]
}
```

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
3. 내장 예시(상의) 실행 → M FIT, 추천 M
   ```powershell
   py ease_check.py
   ```
4. JSON 파일로 실행 → M(31) NO_FIT, 추천 L(32)
   ```powershell
   py ease_check.py ease_request.json
   ```
5. 테스트 → `38 passed`가 나오면 정상
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
| 결과가 전부 `UNDETERMINED` | 단면 행을 변환 없이 넣음 / `size_*` 행을 변환에 넣음 / ML 몸 너비 키를 넣음 | 3장 확인 |
| `사이즈를 찾을 수 없습니다` | 고른 사이즈가 KR 행에 없음 | `garment.sizes`의 `region` 확인 |

---

## 6. 테스트 파일 설명 (`test_ease_check.py`)

| 테스트 | 확인 내용 |
|---|---|
| `test_top_exactly_3cm_is_fit` | 여유 정확히 3.0cm → FIT (경계 포함) |
| `test_top_under_3cm_is_no_fit` | 여유 2.9cm → NO_FIT |
| `test_bottom_needs_both_waist_and_hip` | 하의는 허리·엉덩이 둘 다 3cm 이상이어야 FIT |
| `test_bad_data_is_undetermined` (5건) | 몸 값 없음 / 옷 값 없음 / 단면값 / 비정상 신체값 / 숫자 아님 → UNDETERMINED |
| `test_all_sizes_recommends_smallest_fitting` | 전체 사이즈 판정, 추천 = 입을 수 있는 것 중 가장 작은 여유 |
| `test_unknown_size_raises` | 없는 사이즈 → ValueError |
| `test_rounding_does_not_turn_2_96_into_fit` | 여유 2.96cm → 표시는 3.0이지만 NO_FIT |
| `test_float_error_at_exactly_3cm_is_fit` | 101.1 − 98.1 같은 부동소수 오차에도 3.0 → FIT |
| `test_db_rows_width_is_doubled_to_girth` | 단면 × 2 → 둘레, body 행·총장 행은 건너뜀 |
| `test_db_rows_end_to_end` | 단면 행 → 변환 → 판정, 단면 없는 사이즈는 UNDETERMINED |
| `test_raw_db_width_without_conversion_is_undetermined` | 변환 없이 단면값을 넣으면 UNDETERMINED |
| `test_ml_response_keeps_only_three_girths` | ML 응답에서 둘레 3개만 꺼내고 몸 너비 키는 버림 |
| `test_ml_response_without_male_wrapper` | `"male"` 없이 온 응답도 처리 |
| `test_ml_response_missing_girth_is_undetermined` | 둘레가 없으면 UNDETERMINED |
| `test_korean_category_is_accepted` (3건) | `상의`/`하의`/`TOP` → top/bottom |
| `test_unknown_category_raises` | `아우터` 같은 값 → ValueError |
| `test_region_filter_keeps_kr_only` | KR M / US M이 함께 있으면 KR만 사용 |
| `test_ml_and_db_end_to_end` | ML 응답 + 단면 행 → 판정·추천 |
| `test_size_table_category_is_accepted` (2건) | (임시 경로) `tops`/`bottoms` → top/bottom |
| `test_size_table_rows_used_directly_bottom` | (임시 경로) 탑텐 하의 실제 값 그대로 → M(31) NO_FIT, 추천 L(32) |
| `test_size_table_rows_used_directly_top` | (임시 경로) 무신사 상의 실제 값 그대로 → M FIT (+6.9cm) |
| `test_size_table_rows_must_not_go_through_width_conversion` | `size_*` 행을 단면 변환에 넣으면 UNDETERMINED (× 2 두 번 방지) |
| `test_yejun_api_row_shape_without_basis_key` | 3D 의류 API 조회 결과 형식(`basis` 열 없음)도 처리 |
| `test_measures_sql_matches_3d_api_tables` | `MEASURES_SQL`이 3D API와 같은 테이블·조건을 쓰는지 |
| `test_top_exactly_20cm_is_fit` | 가슴 여유 정확히 20cm → FIT (최대 경계 포함) |
| `test_top_over_20cm_is_too_loose` | 가슴 여유 20.1cm → NO_FIT, `TOO_LOOSE`, "너무 큽니다" |
| `test_top_under_3cm_status_is_too_tight` | 최소 미만 → `TOO_TIGHT`, "작습니다" |
| `test_bottom_hip_over_15cm_is_too_loose` | 엉덩이 여유 15.5cm → NO_FIT |
| `test_bottom_hip_exactly_15cm_is_fit` | 엉덩이 여유 정확히 15cm → FIT |
| `test_bottom_waist_has_no_upper_limit` | 허리 여유 +30cm여도 상한 없음 → FIT |
| `test_too_loose_sizes_are_not_recommended` | 무신사 상의 3XL(+27cm)은 FIT 목록·추천에서 빠짐 |

### `# noqa: E402`란?

```python
sys.path.insert(0, str(Path(__file__).resolve().parent))   # ① 이 파일이 있는 폴더를 경로에 추가
from ease_check import (...)  # noqa: E402                  # ② 그다음 import
```

- 실행에는 영향 없는 주석. 코드 검사 도구(flake8 등)에 "이 줄은 경고하지 마"라고 알리는 표시.
- `E402` = "import가 파일 맨 위에 있지 않음" 경고 번호.
- ①로 `ease_check.py`가 있는 폴더를 먼저 경로에 넣어야 어느 위치에서 pytest를 실행해도 ②가 된다. 의도한 순서라 경고를 끈 것이다.

---

## 7. 서비스 플로우 연결 (인프라 담당 플로우 기준)

```
3-2. [워커] Redis 큐에서 작업을 꺼내 동시에 보냄
       ├─ 신체 API: 사진·키·몸무게 → SAM 11개 → Azure ML → 예측 28개({"male": {...}})
       └─ 의류 API: item_code·size_id → garment.garments·sizes·measures 조회 → Blender → 의류 GLB
★ [워커] 두 결과를 받으면 ease_check 실행
       body  = body_from_ml_response(신체 API가 넘겨준 ML 응답)
       sizes = sizes_from_db_rows(MEASURES_SQL 조회 결과)   ← 의류 API와 같은 테이블
       check_all_sizes(category, body, sizes, 선택 사이즈)
5-2. [웹앱] 모델 링크와 함께 판정 결과를 Redis에 보관 → 브라우저에 전달
5-4. [브라우저] 3D 착장 화면 옆에 판정 결과·부위별 여유분 표시
```

**실행 위치: 웹앱 워커 (제안, 인프라 담당과 결정)**
- 인프라 담당 플로우에서는 ML 예측 결과가 SQL에 저장되지 않고 **신체 API로 바로 돌아온다.**
- 신체 결과와 의류 결과를 **둘 다 받는 곳은 워커**뿐이다.
- 의류 API는 선택한 **사이즈 1개**만 조회하므로, 추천 사이즈까지 내려면 워커가 `MEASURES_SQL`로 **같은 상품의 모든 사이즈**를 조회하거나, 의류 API가 그 행을 함께 넘겨줘야 한다.

| 파트 | 할 일 |
|---|---|
| ML (나) | `ease_check.py`와 입출력 예시 전달. 기준을 바꾸면 `RULES_VERSION` 올림 |
| ML 신체 예측 | `male` 객체에 `chest_girth_cm`, `waist_girth_cm`, `hip_girth_cm` 유지 (이름·둘레 기준) |
| 3D 신체 API | 워커 응답에 ML 예측 치수(최소 둘레 3개) 포함 |
| 3D 의류 API / DB | 6개 상품을 `garment.garments`·`sizes`·`measures`에 단면값으로 등록 (상의 `chest_width`, 하의 `waist_width`·`hip_width`) |
| 웹앱·워커 | `MEASURES_SQL` 조회 + `check_all_sizes()` 호출, 결과를 Redis에 보관 |
| 프론트 | `verdict`, `message_ko`, `parts`, `recommended_size` 표시. UNDETERMINED를 "맞음"처럼 보이게 하지 않음. 판정 숫자를 프론트에 따로 두지 않음 |

### 전달 형식

| 전달물 | 형식 | 이유 |
|---|---|---|
| 코드 | `.py` 파일 1개 | 표준 라이브러리만 써서 웹앱 폴더에 복사 후 `import`만 하면 됨 |
| 입출력 약속 | `.json` 예시 | ML·3D·웹앱이 같은 키 이름으로 맞출 수 있음 |
| 검증 근거 | 테스트 파일 | 받은 쪽에서 `pytest`로 "3cm·20cm·15cm 경계 / 단면 변환 / ML 응답"을 바로 확인 |

### 확인할 것 (3D 담당·DB 담당)
1. 6개 상품을 `garment.garments`·`sizes`·`measures`에 넣을 계획과 일정
2. 탑텐·지오지아는 원본이 **둘레**다 → `garment.measures`에 넣을 때 **÷ 2 해서 단면으로** 넣어야 3D와 ease_check가 같은 값을 쓴다
3. 6개 상품의 `garment.sizes.region` 값 (KR로 넣는지)
4. 지오지아 하의에 `XXL(90)`, `XXL(94)`처럼 같은 `XXL`이 두 개 있음 → `size_label`에 괄호 숫자까지 넣어야 구분됨
