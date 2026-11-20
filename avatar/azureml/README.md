# A 방식: Azure ML 실시간 엔드포인트

SAM 입력의 `sam_measurements` 11개는 측정 실패 시 해당 값에 JSON `null`을 보냅니다.
좌우 둘레는 한쪽이라도 실패하면 null이며, 기본 모델 치수나 0으로 채우지 않습니다.
키·몸무게는 필수 양수입니다. 전체 메시 복원·바인딩·키 보정 실패는 요청을 중단합니다.
11개 모두 null인 입력도 전달하므로 ML 팀은 결측치 지원 범위를 확인해야 합니다.
`score_studio.py`는 null을 숫자형 NaN으로 변환합니다. 등록 모델 자체가 결측값을 지원하거나
학습 당시의 imputer를 포함해야 하며, 이 코드에서는 임의 대체값을 넣지 않습니다.
실제 엔드포인트에도 수정된 `features.py`·`score_studio.py`를 재배포해야 적용됩니다.
출력 28개는 기존대로 모두 양수여야 하며 null은 허용하지 않습니다.

출력 치수 28개의 부위·Size Korea 비교 메모·GLB 계산법은 [ML 예측 신체 치수 정의](<ML 예측 신체 치수 정의.json>)를 참고합니다. 파일 안의 숫자는 예시값이며 실제 예측 결과가 아닙니다.

신체 VM은 사진으로 SAM 메시를 복원하고 치수 11개를 측정합니다. 키·몸무게와 함께 Azure ML의 HTTPS /score 주소에 JSON으로 전송하고 예측 치수 28개를 직접 응답받습니다. 신체 VM 안에 ML 컨테이너나 예측 모델 파일을 배치하지 않습니다.

## 신체 API 설정

avatar/.env의 AZURE_ML_ENDPOINT에 Azure ML Studio의 실시간 엔드포인트 Consume 화면에서 확인한 scoring URI를 지정합니다. 일반 형태는 https://엔드포인트.리전.inference.ml.azure.com/score입니다.

```dotenv
AZURE_ML_ENDPOINT=
AZURE_ML_AUTH=aad_token
AZURE_ML_KEY=
AZURE_ML_DEPLOYMENT=
```

기본 aad_token은 DefaultAzureCredential로 신체 VM 관리 ID를 사용합니다. 엔드포인트도 auth_mode=aad_token이어야 하며 호출 ID에 해당 엔드포인트의 Microsoft.MachineLearningServices/workspaces/onlineEndpoints/score/action 권한이 필요합니다. 이 코드는 권한을 자동으로 부여하지 않습니다. 사용자 지정 관리 ID는 AZURE_CLIENT_ID를 설정할 수 있습니다.

키 기반 엔드포인트를 쓰면 AZURE_ML_AUTH=key와 AZURE_ML_KEY를 비밀 환경으로 설정합니다. 키·토큰을 채팅·Git·로그에 남기지 않습니다. AZURE_ML_DEPLOYMENT는 특정 배포를 지정할 때만 사용하며 비워 두면 엔드포인트의 traffic 설정을 따릅니다.

ML_API_URL·ML_API_AUTH는 더 이상 사용하지 않습니다. HTTP·로컬 ml 주소·다른 도메인·쿼리 토큰·리다이렉트는 허용하지 않습니다. 사설 연결에서도 원래 Azure ML scoring URI를 사용하며 DNS·Private Endpoint·방화벽은 인프라에서 준비해야 합니다.

## 입력 13개와 출력 28개

입력 계약은 schema_version=2, measurement_method=sam_surface_sections_11_v2입니다.

```json
{
  "schema_version": 2,
  "measurement_method": "sam_surface_sections_11_v2",
  "height_cm": 175,
  "weight_kg": 70,
  "sam_measurements": {
    "inseam_cm": 78,
    "hip_girth_cm": 96,
    "hip_width_cm": 35,
    "hip_depth_cm": 24,
    "hip_line_height_cm": 89,
    "ankle_girth_cm": 22,
    "calf_girth_cm": 36,
    "knee_girth_cm": 35,
    "thigh_girth_cm": 54,
    "upper_arm_girth_cm": 29,
    "wrist_girth_cm": 17
  }
}
```

모든 SAM 입력은 raw_sam_cm × 실제 입력 키 / SAM 높이로 보정한 cm 값입니다. 13열의 학습 순서는 model_config.example.json의 input_columns를 따릅니다. 비율이나 사진·메시·request_id는 ML에 보내지 않습니다.

출력은 male 아래 키를 제외한 양수 cm 치수 28개입니다. 누락·null·height_cm 출력은 거절합니다. API가 실제 입력 키를 합쳐 avatar-models의 기본 blend를 변형하고 body-glb에 GLB·앵커·치수 보고서를 저장합니다. SAM 표면은 최종 GLB에 합성하지 않습니다.

## Azure ML 배포 준비

ML팀이 13개 입력·28개 출력 모델을 Azure ML에 등록합니다. 이 폴더를 scoring 코드로 업로드하고 score_studio.py를 진입점으로 지정합니다. features.py·contract.py를 함께 올립니다. 배열 출력의 타깃 순서와 입력 열 이름은 model_config.example.json을 model_config.json으로 복사해 명시합니다. 학습 당시 라이브러리 버전을 environment-studio.yaml에 맞춰야 합니다.

online-endpoint.example.yaml과 online-deployment.example.yaml은 생성 예시입니다. 실제 endpoint 이름·모델 이름·버전·VM 크기·네트워크를 확인한 후에만 사용합니다. 예시는 사설 접근과 Entra 인증이며, 이 작업에서는 Azure 리소스를 생성하지 않았습니다. 배포 컴퓨팅에는 별도 비용이 발생할 수 있습니다.

사용자 지정 팀 예측기를 Azure ML에서 실행하려면 score.py를 진입점으로 사용하고 fitme_predictor.py와 필요한 의존성을 Azure ML 코드·환경에 포함합니다. predict(height_cm=..., weight_kg=..., sam_measurements=...)가 male 치수 28개를 반환해야 합니다. 이것도 신체 VM의 로컬 컨테이너가 아닌 Azure ML 배포입니다.

## 신체 VM 기동

신체 VM에는 SAM 가중치와 원본 모델만 준비한 뒤 다음을 실행합니다.

```bash
cd /opt/fitme-avatar
bash deployment/body-start.sh
```

body-start.sh는 Azure ML 설정을 검사한 뒤 기본 compose.yaml의 avatar와 model-sync만 사용합니다. 로컬 예측기 파일을 요구하지 않습니다. readiness.json의 ml_endpoint_configured는 설정 형식 검사이며 실제 권한·네트워크·추론 성공을 뜻하지 않습니다.

현재 변경은 코드와 예시 설정이며 실제 Azure ML 배포·인증 권한·실사진 추론은 미검증입니다. 입력 단면 측정과 출력 기본 모델의 측정 규격은 다르므로 같은 계약의 학습 입력·목표 쌍이 필요합니다.

참고: [Azure ML 인증](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-authenticate-online-endpoint?view=azureml-api-2), [실시간 엔드포인트 배포](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-deploy-online-endpoints).
