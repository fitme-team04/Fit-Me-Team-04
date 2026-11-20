# 원본 모델 Blob 캐시와 배포

입력 원본은 `fitmemlstdev/garment-models` 컨테이너 바로 아래에서 읽습니다. `models/bundled_garments.json`의 `blob_prefix`는 빈 문자열입니다. 사용자에게 업로드 완료를 전달받았지만 현재 CLI 계정은 파일 목록 읽기·쓰기 권한이 없어 실제 원격 파일 검증은 하지 못했습니다.

원격 파일은 `body_center_back_v19.blend`, `body_center_back_v19.npz`, `black_midrise_straight_v1.blend`, `black_midrise_straight_v1.npz`, `registry.json`, `manifest.json`입니다. 애플리케이션은 이미지에 포함한 신뢰된 manifest의 크기·SHA-256을 사용하며 원격 manifest로 파일 목록을 바꾸지 않습니다.

API 시작 시 파일 캐시를 검증하고 없거나 손상된 원본만 다운로드합니다. 검증된 캐시가 있으면 Azure 인증·다운로드 없이 사용합니다. ETag 고정 다운로드와 임시 파일 검증 후 원자적 교체를 사용합니다. 검증된 버전별 경로를 `GARMENT_TEMPLATE_DIR`로 지정합니다.

```dotenv
GARMENT_MODELS_ACCOUNT_URL=https://fitmemlstdev.blob.core.windows.net
GARMENT_MODELS_CONTAINER=garment-models
GARMENT_MODELS_MANIFEST=/opt/fitme/bundled_garments.json
GARMENT_MODEL_CACHE_DIR=/models/cache
```

Docker는 원본 대신 manifest만 포함하고, Compose의 쓰기 가능한 `garment-model-cache` 볼륨에 원본을 보관합니다. 로컬 CLI 로그인 또는 VM 관리 ID를 `DefaultAzureCredential`로 사용합니다. 키·SAS 파일을 추가하지 않습니다. 결과 GLB는 별도 `garment-glb` 컨테이너를 사용합니다.

**Blender는 상주하지 않습니다.** 요청마다 로컬 원본을 로딩해 작업하고 종료합니다. 최초 다운로드와 요청별 Blender 로딩은 별개입니다. 상의는 뒷목 기준 v19, 하의는 고정 원형 정책이며 자세한 내용은 `garment-generation-policy.md`, `blender-oneshot.md`에 있습니다.

모델 바이너리·ZIP·로컬 배포 묶음은 Git에서 제외합니다. 이미지 재빌드 시 Git에 있는 새 manifest·코드가 필요하고, 원본 변경 시에는 새 핀 해시와 Blob 파일을 함께 배포해야 합니다. 운영 VM 재배포는 수행하지 않았습니다.
