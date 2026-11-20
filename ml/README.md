# FitMe ML 서비스

신체 VM이 보내는 **키·몸무게 + SAM 측정값 11개**를 받아, 사진으로 재지 못하는 상체 치수 17개를 예측하고 **치수 28개**(키 제외)를 돌려주는 Azure ML 실시간 엔드포인트입니다. 입력·출력 계약은 [3D팀 ML 계약](../avatar/azureml/README.md)을 따릅니다.

| 경로 | 역할 |
|---|---|
| `azureml/score_ml.py` | 엔드포인트 진입점. 요청 JSON을 받아 예측기를 부름 |
| `azureml/fitme_predictor.py` | model-s·model-c를 불러와 빈 SAM 값을 채우고 상체 17개를 예측 |
| `azureml/conda_env.yaml` | 배포 환경 `fitme-designer-env` 버전 3 정의 |
| `pipelines/` | Azure ML Designer 파이프라인에 넣은 SQL |
| `samples/` | 테스트 요청 3종과 실제 엔드포인트 응답 |
| `tests/` | Azure ML 없이 돌리는 예측기 회귀 테스트 |

테스트: `python -m unittest discover -s ml/tests -v`

## 모델 2개

데이터: 사이즈코리아 2020~21 성인 **남자** 실측. 알고리즘: Designer **Boosted Decision Tree Regression**(기본값). 학습 80% / 시험 20%.

| 모델 | 입력 | 출력 | 역할 |
|---|---|---|---|
| **model-c** | 키·몸무게 + SAM 11개 (13개) | 상체 17개 | 서비스 핵심. SAM이 못 재는 몸통 위쪽 치수를 채움 |
| **model-s** | 키·몸무게 (2개) | SAM 11개 | 사진 측정이 실패한 SAM 값만 채움 |

- SAM 11개: `inseam_cm`, `hip_girth_cm`, `hip_width_cm`, `hip_depth_cm`, `hip_line_height_cm`, `ankle_girth_cm`, `calf_girth_cm`, `knee_girth_cm`, `thigh_girth_cm`, `upper_arm_girth_cm`, `wrist_girth_cm`
- 상체 17개: `torso_length_cm`, `shoulder_width_cm`, `arm_length_cm`, `waist_line_height_cm`, `chest_line_height_cm`, `belly_girth_cm`, `waist_girth_cm`, `waist_width_cm`, `waist_depth_cm`, `chest_girth_cm`, `chest_width_cm`, `chest_depth_cm`, `back_width_cm`, `underbust_girth_cm`, `belly_front_cm`, `hip_rear_cm`, `rise_arc_cm`

Designer Train Model은 정답 열을 하나만 받기 때문에, 두 모델 모두 데이터를 `item`(어떤 치수인지) + `value`(값)로 **세로로 쌓아 모델 하나**로 학습했습니다. 부스팅 트리는 첫 분기에서 `item`으로 갈라 항목마다 다른 규칙을 배웁니다.

## 성능 (시험 데이터, 평균 절대 오차 cm)

**model-c** — 전체 MAE **1.60**, RMSE 2.22 (시험 613명. 밑가슴둘레·가슴선 높이는 394명)

| 항목 | MAE | 항목 | MAE |
|---|---|---|---|
| 허리둘레 | 3.09 | 가슴선 높이 | 1.45 |
| 밑가슴둘레 | 2.76 | 허리선 높이 | 1.32 |
| 배둘레 | 2.64 | 어깨너비 | 1.27 |
| 가슴둘레 | 2.41 | 팔길이 | 1.22 |
| 밑위둘레 | 2.27 | 허리두께 | 1.19 |
| 등너비 | 1.81 | 가슴두께 | 1.04 |
| 몸통길이 | 1.57 | 허리너비 | 0.98 |
| | | 가슴너비 | 0.94 |

**model-s** — 시험 약 1,050명 (위팔둘레 640명, 엉덩이두께 633명)

| 항목 | MAE | 항목 | MAE |
|---|---|---|---|
| 엉덩이선 높이 | 1.80 | 종아리둘레 | 1.17 |
| 넓적다리둘레 | 1.77 | 엉덩이두께 | 1.14 |
| 엉덩이둘레 | 1.72 | 무릎둘레 | 1.00 |
| 다리안쪽길이 | 1.63 | 엉덩이너비 | 0.82 |
| 위팔둘레 | 1.21 | 발목둘레 | 0.73 |
| | | 손목둘레 | 0.62 |

- 전체 R²는 항목이 섞여 있어 0.99대로 부풀려지므로 성능 기준으로 쓰지 않고 항목별 MAE를 봅니다 (`pipelines/per_item_mae.sql`).
- model-c 오차는 몸통 둘레에서 가장 큽니다. SAM 입력이 엉덩이·다리·팔 위주라 몸통 위쪽 정보가 없기 때문입니다.
- 학습 데이터는 줄자 실측, 서비스 입력은 SAM 3D 단면 측정이라 측정 방식 차이로 실제 오차는 더 클 수 있습니다. 실사진 검증이 필요합니다.

## 요청 처리 순서

```
요청 (키·몸무게 + sam_measurements 11개, 실패 항목은 null)
  → null·NaN·0 이하·무한대·숫자가 아닌 값은 "빈 값"으로 봄
  → 빈 값이 있으면 model-s가 그 항목만 채움 (정상 측정값은 덮어쓰지 않음)
  → model-c가 채운 11개 + 키·몸무게로 상체 17개 예측
  → {"male": {...}} 28개 응답 (null 없음, 키 제외)
```

| 받은 SAM | model-s | model-c | 결과 |
|---|---|---|---|
| 11개 | 거치지 않음 | 예측 | 가장 정확 |
| 1~10개 | 빈 항목만 채움 | 예측 | 받은 실측만큼 정확 |
| 0개 | 11개 전부 채움 | 예측 | 키·몸무게 기반 추정 |

`schema_version`, `measurement_method`가 함께 와도 무시합니다. 어떤 항목을 채웠는지는 엔드포인트 로그에 `estimated SAM fields`로 남습니다. 요청 예시와 실제 응답은 `samples/`에 있습니다.

## 배포 현황

| 항목 | 값 |
|---|---|
| 워크스페이스 | `fitme-mlw-dev` (Korea Central) |
| 엔드포인트 | `fitme-ml-v3` (관리형, Key-based 인증) |
| 배포 | `green` — 트래픽 100% |
| 모델 | `fitme-models:1` (폴더 `model-c/`, `model-s/`에 Designer Train Model 출력 각 7개) |
| 환경 | `fitme-designer-env:3` (`azureml/conda_env.yaml`) |
| VM | `Standard_NC4as_T4_v3` × 1 |

주소와 키는 Azure ML Studio → Endpoints → `fitme-ml-v3` → **Consume**에서 확인합니다. **키는 Git·채팅·로그에 남기지 않습니다.** 신체 VM은 `AZURE_ML_AUTH=key`, `AZURE_ML_KEY`로 호출합니다.

## 다시 배포하는 법

1. **모델 등록**: 각 파이프라인 Job의 Train Model → Outputs + logs에서 `trained_model_outputs` 파일 7개를 내려받아 `fitme-models/model-c/`, `fitme-models/model-s/`로 묶고, Models → Register → From local files → **폴더**로 업로드합니다. 관리형 배포는 배포 하나에 모델 하나만 연결되므로 두 모델을 한 폴더로 묶습니다. 예측기는 `_schema.json`에 SAM 열이 있으면 model-c, 없으면 model-s로 구분합니다.
2. **환경**: Environments → Custom → 이미지 `mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu20.04:latest` + `azureml/conda_env.yaml`.
3. **배포**: 엔드포인트 → Add deployment → 모델 `fitme-models`, Scoring script `score_ml.py`, Optional script `fitme_predictor.py`, 위 환경, VM `Standard_NC4as_T4_v3` × 1. 새 배포는 트래픽 0%로 올리고, 테스트 후 트래픽을 넘깁니다.
4. **테스트**: Test 탭에 `samples/request_*.json` 3개를 넣어 `samples/response_*.json`과 비교합니다.

## 겪은 문제와 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| Designer → ACI 배포 실패 (`containerGroups/write` 권한 없음) | 옛 ACI 방식, 신체 VM 코드도 관리형 HTTPS 주소만 허용 | 관리형 온라인 엔드포인트로 변경 |
| 모델 등록 시 `Data asset ... is invalid` | 파이프라인 이름의 한글이 자산 이름에 들어감 | 파이프라인·모델 이름을 영어로 |
| 환경 빌드 실패 (`azureml-inference-server-http~=1.4`) | `azureml-defaults` 최신이 Python 3.9+ 추론 서버 요구 | `azureml-defaults` 빼고 추론 서버 1.3.4 고정 |
| 컨테이너 시작 직후 종료 (`No module named 'azureml.studio.core'`) | `azureml-designer-core` 0.0.87이 빈 패키지 | 0.0.80 고정 |
| CPU VM 선택 불가 (Available quota 0 cores) | 구독 할당량이 GPU(NCasT4) 계열에만 있음 | 가장 작은 `NC4as_T4_v3` × 1. 기본값이 NC16 × 3이라 꼭 바꿀 것 |
| 숫자 입력 2개가 `String`으로 학습됨 | 원본 CSV에 글자 형식 저장 | SQL에서 `CAST(... AS REAL)` |
| Test 탭에서 새 배포를 골라도 옛 배포가 응답 | Test 요청이 트래픽 비율대로 전달됨 | 테스트할 배포로 트래픽을 넘긴 뒤 테스트 |
| 실패한 엔드포인트 삭제 실패 (`scope ... locked`) | 스토리지 `fitmemlstdev` 삭제 잠금 | 인프라 담당자에게 요청. 배포가 없는 엔드포인트는 비용 없음 |
| 로그의 `flavor is missing` Traceback | Designer 로더가 여러 방식을 차례로 시도한 기록 | 무시 (`This does not mean model loading failed`) |

## 비용

배포 VM이 켜져 있는 동안 시간당 약 $0.65가 나갑니다. 쓰지 않을 때는 배포 `green`을 지우면 VM 비용이 멈춥니다. 엔드포인트 자체 삭제는 스토리지 잠금 때문에 인프라 담당자에게 요청합니다.
