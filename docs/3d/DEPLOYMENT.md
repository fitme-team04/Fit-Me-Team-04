# 3D VM 배포

## 위치와 비밀 설정

## 현재 연결 확인 상태

### 완성된 GLB 자동 업로드 설정

실제 테스트 파일은 업로드하지 않습니다. Blender 생성이 끝나면 각 서비스의
`src/core/runtime.py` → `src/storage/blob_assets.py`의 `publish()`가 자동으로 게시합니다.

| 서비스 | `.env`의 결과 컨테이너 | 저장 경로 |
|---|---|---|
| 신체 | `body-glb` | `v2/avatars/<사용자 해시>/<GLB 해시>/model.glb` |
| 의류 | `garment-glb` | `v2/garments/<GLB 해시>/model.glb` |

계정 주소는 양쪽 모두 `https://fitmemlstdev.blob.core.windows.net`입니다.
GLB는 `model/gltf-binary` 형식으로 저장하고 앵커 JSON을 마지막 완료 표식으로 게시합니다.
신체는 `measurements.json`도 저장합니다. 업로드 후 15분 읽기 URL을 반환하며 URL·토큰은 로그로 출력하지 않습니다.
기존 해시 경로의 파일은 덮어쓰지 않습니다.

인증은 `DefaultAzureCredential`이 VM 관리 ID를 사용합니다. 결과 Blob용 계정 키·SAS는 설정하지 않습니다.
실행 VM 관리 ID에는 결과 컨테이너 쓰기 권한과 사용자 위임 SAS 발급 권한이 필요합니다.
컨테이너 범위의 Storage Blob Data Contributor를 사용할 경우 스토리지 계정 범위의 Storage Blob Delegator도 검토합니다.
이 문서와 코드 설정만으로 Azure IAM 권한이 부여되지는 않습니다. 실제 업로드와 VM 권한은 검증하지 않았습니다.

로컬 Azure CLI Entra 로그인으로 `fitme-sql-dev/fitme` 접속과 `garment.garments/sizes/measures`,
측정 관련 테이블의 SELECT 권한을 확인했습니다. SQL 비밀번호·스토리지 키는 조회하지 않았습니다.
SQL API는 로컬 PC에서 실행하지 않습니다. garment/.env는 VM용 `AZURE_SQL_AUTHENTICATION=ActiveDirectoryMsi`를 사용합니다.
신체와 ML은 SQL을 사용하지 않고 FastAPI JSON으로 직접 통신합니다. ODBC 18은 의류 컨테이너에만 설치합니다.
신체의 JSON 입력 계약과 실행 방법은 [ML 안내](../../avatar/azureml/README.md)를 따릅니다.
2026-11-12 SQL 중계 방식을 취소하고 빈 임시 테이블·전용 신체 VM SQL 사용자·권한을 제거했습니다.
상품·실측과 의류 서비스 SQL은 유지합니다. 만료 행 정리 작업도 필요하지 않습니다.

원본 모델은 `fitmemlstdev/avatar-models`, 결과는 `body-glb`·`garment-glb`로 설정했습니다.
2026-11-12 원본 Blob 권한 수정 후 계정 로그인으로 네 모델의 목록 조회·실제 다운로드·크기·SHA-256 검증에 성공했습니다.
검증용 로컬 파일은 avatar/.cache/blob-check/에 저장하며 Git에서 제외합니다.
신체 VM 기동 후 /opt/fitme-avatar에 소스와 모델 다운로드 환경을 배포하고 VM 관리 ID로 원본 네 파일 다운로드·해시 검증까지 완료했습니다. GPU는 Tesla T4이며 NVIDIA 컨테이너 런타임도 구성되어 있습니다. SAM 추가 체크포인트·치수 예측 모델이 없어 컨테이너 빌드·기동과 실제 사진 추론은 미실행입니다. [실제 배포·테스트 절차](../../avatar/DEPLOYMENT_TEST.md)를 따릅니다.
같은 계정의 body-glb·garment-glb 파일 목록 조회는 아직 권한 오류입니다. 결과 업로드와 VM 관리 ID 권한은 미검증입니다.
역할 변경·키 조회·테스트 파일 업로드는 하지 않았습니다.
모델 읽기 권한과 결과 쓰기 권한은 계정·실행 VM 관리 ID 각각에 필요한 범위로 검토해야 합니다.
ML은 실제 학습 모델이 준비될 때까지 실모델 추론이 미검증입니다. 기본 구성은 Azure ML 실시간 엔드포인트입니다.

작업 폴더는 GPU VM의 `avatar/`, CPU VM의 `garment/`입니다.
이전 로컬 `.env`와 `.env.models`는 새 서비스 위치로 복사했으며 Git·Docker 빌드에서 제외합니다.
새 VM에서는 `.env.example`을 `.env`로, avatar의 `.env.models.example`을 `.env.models`로 복사합니다.
기존 비밀값을 예시 파일이나 Git에 저장하지 않습니다.

## GPU 신체 API

### A 방식: Azure ML 실시간 엔드포인트

신체 VM에는 avatar API와 model-sync만 실행합니다. ML팀이 Azure ML에 등록·배포한 모델의 HTTPS scoring URI를 AZURE_ML_ENDPOINT에 설정합니다. 기본 인증은 AZURE_ML_AUTH=aad_token이며 VM 관리 ID에 엔드포인트 호출 권한을 준비해야 합니다. 키 인증은 AZURE_ML_AUTH=key와 비밀 AZURE_ML_KEY로 선택할 수 있습니다.

입력은 실제 키·몸무게·SAM cm 치수 11개, 출력은 키 제외 치수 28개입니다. Azure ML의 score_studio.py·features.py·contract.py와 전용 환경을 함께 배포합니다. [ML 배포·인증 계약](../../avatar/azureml/README.md)을 따릅니다.

```bash
cd avatar
docker compose up --build -d
docker compose logs model-sync
```

`model-sync`가 `fitmemlstdev/avatar-models`의 `mhr_model.pt`, `fitme_depth_fixed.blend`,
`a_pose.npz`, `sam_body.npz`를 내려받아 명세의 크기·SHA-256을 검증한 뒤 API 시작을 허용합니다.
모델 캐시는 API에 `/models` 읽기 전용으로 연결합니다. 원본 파일과 validation 결과물은 커밋하지 않습니다.
인증은 `.env.models`의 연결 문자열 또는 읽기 SAS를 사용하거나, 비밀값 없이 VM 관리 ID에
컨테이너의 Storage Blob Data Reader 권한을 부여합니다. 로컬 Azure CLI 로그인은 호스트 다운로드에서 사용할 수 있습니다.

Docker 없이 다운로드할 때:

```bash
python -m pip install -r requirements-models.txt
python scripts/download_blob_models.py --env-file .env.models
```

SAM 사진 추론용 체크포인트는 별도로 준비합니다. 승인된 HF 계정의 `HF_TOKEN`을 설정하고
`scripts/download_models.py`를 실행한 뒤 `scripts/check_assets.py --with-checkpoints`로 검사합니다.
SAM 환경은 Docker의 `/opt/conda/bin/python`, API는 `/opt/api/bin/python`을 사용합니다.
자산 검사 스크립트는 NumPy가 있는 SAM 환경에서 실행합니다.

현재 기본 방식은 Azure ML 실시간 엔드포인트이며 로컬 ML 컨테이너·예측 모델 파일은 필요하지 않습니다.
API와 Azure ML은 버전 2의 13개 입력·28개 출력 계약을 함께 사용합니다. 실제 모델은 ML팀에서 별도로 준비·배포해야 합니다.

## CPU 의류 API

```bash
cd garment
docker compose build
docker compose run --rm garment python -m checks.check_db
docker compose run --rm garment python -m checks.check_generation
docker compose up -d
```

Python은 ODBC Driver 18 + pyodbc를 사용합니다. `.env`에서 `AZURE_SQL_AUTHENTICATION=SqlPassword`와
서버·DB·SQL 사용자·비밀번호를 설정하거나, VM 관리 ID를 준비한 뒤 `ActiveDirectoryMsi`로 설정합니다.
`AZURE_SQL_CONNECTION_STRING`이 있으면 다른 SQL 설정보다 우선합니다. TLS 인증서 검증을 유지합니다.
관리 ID를 쓰려면 Azure SQL 사용자·권한과 네트워크 접근을 따로 준비해야 합니다.

상품·사이즈·실측은 기존 `garment.*`를 직접 조회합니다. SQL은 [공통 Azure 3D 폴더](../../db/azure/3d/README.md)에 한 번만 유지합니다.
별도 레시피 테이블은 사용하지 않습니다. 요청은 `{"item_code":"E422992-000","size_id":3}`입니다.
category의 상의→crewneck_v1, 하의→slacks_v1로 매핑하고, ref.measure_aliases의 출처별 sleeve_length 별칭을 조회합니다.
소매 측정 기준이 없거나 충돌하는 경우, 필수 실측이 부족한 경우는 422를 반환합니다.
새 의류 API를 배포한 뒤 `db/azure/3d/03_remove_recipe.sql`로 비어 있는 구형 테이블을 제거합니다.
모든 서비스의 결과 Blob 인증은 별도로 VM 관리 ID를 사용하므로 원본 모델용 SAS 설정과 구분합니다.

## 개발 실행과 점검

컨테이너의 API 작업 위치는 `/app/src`입니다.
GPU는 `uvicorn api.avatar:app --port 8001`, CPU는 `uvicorn api.garments:app --port 8002`로 실행합니다.
Blender 작업은 `src/geometry/`, SAM 작업은 `src/inference/`의 실제 파일 경로로 호출합니다.
`/health`는 프로세스 생존만 확인합니다. 실제 SQL·Blob·GPU 통합은 별도로 확인해야 합니다.

```bash
python -m unittest discover -s tests -v
```

실제 Azure 마이그레이션·GPU Docker 빌드는 이관 작업에서 실행하지 않습니다. 변경은 feature/3d-deploy에 저장합니다.
