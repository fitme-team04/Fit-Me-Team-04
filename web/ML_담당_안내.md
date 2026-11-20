# 입어봄 웹앱 — ML 담당용 안내

## 중고 의류 촬영 결과 연결

여기서 설명하는 API는 **판매자의 착용샷에서 해당 옷의 실측을 추출**하기 위한 웹앱 규격이다. 3D팀의 `3D.zip`에 있는 `POST /api/garments`는 Azure SQL 카탈로그의 상품·사이즈 ID로 GLB를 생성한다. 구매자의 신체 모델은 별도 `POST /api/avatars`에서 구매자 본인의 사진과 키·몸무게를 사용한다. [3D팀 소스에서 확인한 실제 입력과 응답](../docs/3d/README.md)

V2는 판매자의 착용샷을 FastAPI에서 Redis로 보내고, 미디어 워커가 VM에 측정을 요청한다. VM은 한 벌의 의류 치수를 반환하며, 해당 옷의 GLB를 Blob에 저장했다면 응답에 `model_blob`도 포함한다. 워커가 MySQL에 결과를 저장하고 Redis로 응답을 돌려준다. 구매자 핏 추천과 매물 공유는 Redis의 DB 워커가 담당한다. [V2 실행 안내](README.md)

- 판매자가 ‘이 사진을 보내 측정하기’를 누르면 브라우저에서 사진의 긴 변을 최대 1600px로 맞추고 JPEG로 인코딩한다. FastAPI가 바이트를 받아 설정된 서버로 `POST`한다. `Content-Type: image/jpeg`, 최대 4 MiB, 응답 대기 35초다. 외부 주소는 HTTPS, 같은 머신의 테스트 서버는 HTTP도 지원한다.
- 측정 서버는 완료된 항목만 아래 JSON으로 반환한다. `measurements`의 키는 `ref.measure_definitions`의 의류 항목이다. 너비는 옷의 평면 단면(cm)이다. 인체 둘레, 신체 모델의 목표 치수, 이미지 픽셀 폭은 다른 측정 기준이다.

```json
{"basis":"garment","unit":"cm","category":"상의","measurements":{"chest_width":55,"garment_shoulder_width":51,"body_length":69,"sleeve_length":21.5}}
```

위 숫자는 포맷 설명에 사용한 커버낫 카탈로그 값이다. V2의 브릭 티셔츠 체험에는 별도의 ‘시연용 예시’ 치수를 사용한다. VM에서 온 치수는 ‘ML 추정’, 팀 파일에서 읽은 치수는 ‘ML 결과 파일’로 표시한다. `model_blob`에는 워커에 설정한 컨테이너 안의 상대 GLB 이름을 넣는다. 예를 들어 `jobs/abc123/garment.glb`다. 워커에서 받은 `Idempotency-Key`가 같으면 VM도 같은 측정 결과를 돌려주는 것이 좋다.

**중고 매물의 추천.** 측정한 옷의 카드를 구매자가 열면, 앱이 매물 치수와 키·몸무게만 `POST /api/resale/recommend`에 보낸다. `web/team_bridge.py`의 `estimate_from_height_weight`가 성별 구분 없이 가까운 실측 표본을 찾아 신체 치수를 추정하고, `web/listing_fit.py`의 `_quick_comparison`이 그 한 벌의 부위별 여유를 비교한다. 비교에 쓸 부위나 비슷한 체격의 표본이 부족하면 판단을 보류한다. 표본 거리·최소 표본 수와 의류 종류별 여유 기준은 착용 검증 후 조정할 지점이다.

아래부터는 별도 실험실(`/static/fit-lab.html`)의 카탈로그 사이즈 비교에 관한 안내다. 그 화면의 추정·사이즈 선택은 `web/sizing.py`에서 팀 `db/예시_코드`의 `_추정.py`와 `_추천.py`를 호출한다.

---

## 1. 받아서 실행

이 코드는 팀 `feature/poc-db-env` (v0.2.0)에 웹앱(`app/`)을 더한 `feature/front-test` 브랜치입니다.

1. 저장소에서 `feature/front-test` 브랜치로 이동
2. `windows_setup.cmd` 더블클릭 (관리자 확인 → 예). `~/poc-size-ai` 를 이 내용으로 다시 반영하니, 거기서 직접 고친 파일이 있으면 먼저 옮겨 두세요
3. `windows_app.cmd` 더블클릭 → 브라우저 http://localhost:8000 (오른쪽 위 배지 "DB 연결" 이면 팀 MySQL 사용 중)

VM 이면: 저장소에서 `bash setup.sh` → `cd ~/poc-size-ai && bash web/run.sh`

## 2. 요청 한 번이 지나가는 길

```
화면 POST /api/recommend  {item_code, region, gender, height_cm, weight_kg, fit, my_garment?, measures?}
  └ main.py  recommend()
      └ sizing.py  recommend(req)
          ① team_check.validate(...)                ← 팀 _검증.py
          ② catalog.find_product(item_code, region)  ← 팀 _추천.size_rows / group_by_size (garment.*)
          ③ _estimate_body(mode, gender, h, w)       ← 팀 _추정.estimate (k-NN, k=5)     ★ 교체 지점 A
          ④ _score_size(...) 사이즈마다               ← 팀 _추천.ease_for_size (옷 × factor − 몸)
          ⑤ _pick_by_mine(...) 또는 _pick_by_body(...) ← 이 앱의 선택 규칙                 ★ 교체 지점 B
          ⑥ _team_baseline(...)                       ← 팀 _추천.rank_key (기준선, 비교용으로 응답에 같이 넣음)
      └ explain.py  explain(result)  → 설명 문장 (Azure OpenAI 는 숫자를 만들지 않고 설명만)
```

## 3. 모델로 바꿀 자리

### ★ A. 몸 치수 추정 — `sizing.py` 의 `_estimate_body`
- 지금: DB 모드는 팀 k-NN(`_추정.estimate`, `knn_baseline_v1`), 데모 모드는 단순 식
- 입력: `gender`, `height_cm`, `weight_kg` → 출력: `{measure_code: cm}` (예: `chest_girth`, `shoulder_width`, `waist_girth` …)
- 모델로 바꿀 때 이 함수의 반환 모양 `(body dict, maps, 추정기 이름)` 만 지키면 나머지는 그대로 동작
- 사용자가 직접 잰 치수(`measures`)가 오면 추정값을 덮어씀 → 화면 "계산 근거 자세히" 에 `추정/입력` 구분 표시

### ★ B. 사이즈 선택 — `sizing.py` 의 `_pick_by_body`
- 지금 규칙: 작은 사이즈부터 보며 **결정 항목** 여유분이 모두 기준 이상인 첫 사이즈
  - `DECIDING_CODES = chest_girth, waist_girth, hip_girth, shoulder_width`
  - 둘레 항목 기준 = `FIT_EASE_CM` → 정핏 **6cm**, 여유핏 **12cm** (UI 쪽 임시값 — 정해 주세요)
  - 어깨는 ≥ 0
  - 만족하는 사이즈가 없으면 가장 큰 사이즈 + `fallback: true`
- `FIT_EASE_CM` 을 0 으로 두면 팀 `_추천.py` 기준선(여유분 ≥ 0 중 평균 여유분 최소)과 같아짐
- 응답의 `team_baseline` 에 기준선 결과가 항상 같이 들어 있어서 **앱 규칙 vs 기준선 vs 모델** 비교가 바로 됨
- 분류 모델(사이즈 예측, 팀 `ai/3_고급/06_분류_사이즈_예측.py`)로 바꿀 때: 입력 = 몸 치수 + 선호 핏(+ 상품 사이즈표), 출력 = `size_label` 하나. `scored` 목록에서 그 라벨을 찾아 돌려주면 됨

### 내 옷 기준 — `_pick_by_mine`
- 사용자가 "잘 맞는 옷" 실측(가슴단면·어깨너비·총장)을 넣으면 몸 추정보다 우선: 내 옷과 절댓값 차이 평균이 가장 작은 사이즈

## 4. 직접 돌려 보기

API 문서(눌러서 실행): http://localhost:8000/docs

Rocky8 터미널에서 한 번 호출:

```bash
curl -s -X POST http://localhost:8000/api/recommend -H 'Content-Type: application/json' -d '{"item_code":"E422992-000","region":"KR","gender":"male","height_cm":175,"weight_kg":75,"fit":"regular"}'
```

서버 없이 파이썬에서 여러 체형을 한꺼번에 (Rocky8, `~/poc-size-ai/app` 에서):

```bash
../.venv/bin/python -c "
import sizing
for h, w in [(165,60),(170,65),(175,75),(180,85)]:
    r = sizing.recommend({'item_code':'E422992-000','region':'KR','gender':'male','height_cm':h,'weight_kg':w,'fit':'regular'})
    print(h, w, r.get('recommended'), 'baseline', r.get('team_baseline'), 'fallback', r.get('fallback'), r.get('errors'))
"
```

응답 주요 필드: `recommended` · `compare_with` · `basis`(body / my_garment) · `fallback` · `team_baseline` · `estimator` · `body_used`(값 + 추정/입력) · `sizes[]`(사이즈별 `ease`·`status`·`diff_vs_mine`) · `rule` · `warnings`

## 5. 지금 데이터로 보이는 한계 (확인 부탁)

| 항목 | 현재 | 영향 |
|---|---|---|
| 크루넥T(E422992-000) 옷 실측 | 예시 DB 에 **KR M · US M 만** 있음 | DB 모드에서는 비교할 사이즈가 하나라 항상 M + `fallback` |
| 실측자(measured) 수 | 예시 DB 기준 몇 명 | k-NN 추정 오차 큼 (ANSUR II·BodyM 전체 적재 후 재확인) |
| `arm_length ↔ sleeve_length` (factor 1) | 반팔 소매길이와 팔길이를 바로 비교 | 반팔은 항상 음수 → 그래서 결정 항목에서 뺐고 표에만 표시 |
| 정핏/여유핏 여유분 | 6 / 12cm (근거 없는 임시값) | 결과를 좌우하는 핵심 값 |

## 6. 결정해 주시면 바로 반영할 것
1. 정핏·여유핏 기준 — 고정 여유분(cm)? 비율? 사이즈 분류 모델?
2. 몸 치수 추정 — k-NN 유지 / 회귀 / 다른 모델, 어떤 치수까지 추정할지
3. 결정 항목 — 가슴·허리·엉덩이·어깨 외에 총장 등을 넣을지
4. 평가 지표 — 기준선 대비 무엇으로 비교할지 (FigJam: 상품 확인 성공률·완료 시간·설명 이해도 + 착용 후 평가)
5. Azure ML — 모델을 **Azure ML 온라인 엔드포인트**로 올리면, 웹앱은 `_estimate_body` / `_pick_by_body` 에서 그 주소를 호출하고 실패하면 지금 규칙으로 돌아가게 붙일 예정 (엔드포인트 주소·입출력 모양만 정해 주세요)

전체 구조·Azure 배포는 `web/README.md`, 실행 절차는 `실행_가이드.txt` 5번.
