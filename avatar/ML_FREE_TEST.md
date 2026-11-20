# ML 없이 신체 생성 테스트

이 버전은 Azure ML 요청·응답·인증 없이 예시 치수 28개로 기본 신체를 변형합니다.
사진 검증, SAM 복원과 측정 11개, Blender 변형, Blob 게시와 웹 연결은 유지합니다.
따라서 사진·SAM 체크포인트·GPU 환경·기본 모델·Blob 권한은 여전히 필요합니다.

## 실행

신체 VM의 서비스 디렉터리(`/opt/fitme-avatar`)에 이 브랜치의 코드를 배포한 후 실행합니다.
기존 `.env`와 `.env.models` 설정을 사용하되 Azure ML 주소·키·권한은 필요하지 않습니다.

```bash
docker compose -f compose.yaml -f compose.ml-free.yaml up -d --build
```

또는 `.env`에 `FITME_PREDICTION_MODE=example`을 설정하면 기존 `infra/deploy/body-start.sh`도
ML 설정 검사를 건너뜁니다. 기본값 `azure_ml`은 기존 실제 Azure ML 경로입니다.
Compose 오버라이드가 켜져 있으면 `.env` 값보다 우선합니다.

웹에는 기존과 같은 `body`·`garment` 결과를 반환하며 `body.measurements_url`도 포함합니다.
웹의 사진·키·몸무게·상품·사이즈 입력 형식은 바뀌지 않습니다.

## 예시 치수의 의미

`src/core/test_measurements.json`은 키 175cm 기준 기본 모델 변형 예시입니다.
28개 값에 `입력 키 / 175`를 곱합니다. 몸무게·SAM 치수에 따라 체형을 예측하지 않습니다.
이 결과를 실제 ML 예측이나 실제 사용자 치수로 해석하면 안 됩니다.
GLB의 scene extras에 `fitme_prediction_source: "example"`을 기록하여 실제 결과와 구분합니다.
ML 오류가 나면 자동으로 예시값을 사용하는 동작은 없습니다.

## 실제 ML로 복귀

`.env`의 `FITME_PREDICTION_MODE=azure_ml`과 실제 Azure ML 설정을 적용하고
오버라이드 없이 컨테이너를 다시 생성합니다.

```bash
docker compose -f compose.yaml up -d --force-recreate avatar
```

이 문서의 명령은 배포 안내입니다. 코드 작성 과정에서 VM 배포나 실제 Blob 업로드는 수행하지 않습니다.
