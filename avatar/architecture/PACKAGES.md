> Current implementation: Blender runs per request and is not resident. Verified original files stay cached on VM disk. SAM residency is unchanged. Current source is authoritative; earlier versioned modeling notes below are historical.

> Body responses include the three ML girths; failures return null girths. Body jobs use independent object/mesh/shape-key copies. See ../docs/blender-oneshot.md.

# 신체 서비스 패키지 역할

| 위치 | 역할 |
| --- | --- |
| src/core/sam_runtime.py | SAM 상주 프로세스 수명·재사용·시간 초과·재시작 관리 |
| src/core/error_logging.py | 422·503 detail 및 검증 오류 필드의 로그 기록 |
| src/core/photo.py | 고해상도 사진 축소·EXIF 방향 보정·SAM 입력 JPEG 생성 |
| src/core/runtime.py | Blender 작업과 메모리 파일 대체 경로·결과 Blob 게시 |
| src/core/test_prediction.py·test_measurements.json | ML 없는 테스트 모드·키 비례 예시 치수 28개 |
| compose.ml-free.yaml·ML_FREE_TEST.md | 예시 모드 실행 설정·사용 안내 |
| src/api | 사진 처리·Azure ML 호출·기본 모델 변형 연결 |
| src/core/features.py | cm 측정값 11개·키·몸무게 입력 계약 및 항목별 null 정리 |
| src/api | 사진 처리·SAM 직접 메시 생성 연결, 기존 ML 보조 함수 유지 |
| src/core/sam_surface.py | SAM 신체·가이드의 동일 배율 키 보정 및 바닥 정규화 |
| src/geometry/sam_avatar_worker.py | SAM 정점·삼각형 직접 GLB·앵커·출처별 측정 보고서·단면 선택 진단 |
| src/core/features.py | cm 측정값 11개·키·몸무게 입력 계약 |
| src/core/contract.py | 예측 28개 검사 및 실제 키 결합 |
| src/core/ml_endpoint.py | Azure ML 설정·인증 |
| src/inference | SAM 추론·A 포즈 |
| src/geometry | SAM 단면 측정·SAM 직접 GLB, 기존 기본 모델 변형 도구 |
| src/storage | 원본·결과 Blob |
| azureml | Azure ML 등록·사용자 지정 모델 scoring 코드와 배포 예시 |
| infra/deploy/body-start.sh | SAM 자산 검사 및 신체 API 기동, 원격 ML 설정 불필요 |

신체 API는 FastAPI·httpx·azure-identity·azure-storage-blob을 사용합니다. Blender·SAM 의존성은 기존 환경을 유지합니다. ML 학습 의존성은 Azure ML 전용 환경에 설치합니다. SQL·로컬 ML 컨테이너는 사용하지 않습니다.


### Body girths and fit judgement API
`core/runtime.render` adds ML male chest/waist/hip girths to successful avatar receipts through `core/body_girths.py`. `core/error_logging.py` preserves failure status/detail/headers and emits null girths for HTTP, validation and unhandled failures on /api/avatars. These are predicted inputs, not post-deformation mesh measurements.


### Resident body Blender with request copies (current)
`api.avatar.lifespan` starts `core.blender_runtime.resident` before SAM and stops both in nested finally blocks. `measure_surface` and `core.runtime.render` use the same resident Blender by default. `geometry.resident_worker` opens FITME_TEMPLATE once, then `template_copy.request_body` deep-copies the object/mesh/shape keys for each measurement or render and removes the copy on success/error. `deform.solve` accepts an optional body object; worker.generate returns GLB bytes without touching the template. Per-request Blender object/mesh/key counts are checked; timeout or cleanup failure kills the process, next request reloads. AVATAR_BLENDER_MODE=oneshot remains a rollback path. Real 175-182-175 GLBs were identical for A/A, source file/key hashes and data counts stayed fixed, a failed request and SAM measurement reused the same process. See docs/resident-blender.md and scripts/test_blender_resident.py.


### Current policy: oneshot Blender, disk model cache only
The API no longer starts or calls resident Blender. Avatar measures SAM surfaces and renders body copies with per-job subprocess.run; SAM inference residency is unchanged. Garment lifespan verifies/downloads model files only, and runtime launches Blender per request. All original cache/Blob paths, center-back shirt and static pants policies stay unchanged. Temporary output descriptors and request copies are cleaned up. Resident helper modules are historical/manual tools, not API paths. See docs/blender-oneshot.md.


`../scripts/build_fit_test_bodies.py` generates synthetic body fixtures using the avatar geometry package; it was moved from the garment scripts to keep service imports isolated.

### 전신 사진 프레이밍 검사

- `src/core/photo_visibility.py`: 기존 NumPy로 원본 이미지 크기·사람 bbox·MHR70 예측 투영 좌표를 검사합니다. 경계 여유·이미지/검출 영역 지지 수치를 JSON으로 반환하며 누락/잘림은 안전한 `PhotoFramingError.reason`과 정적 재촬영 안내로 구분합니다. 독립 2D 가시성 신뢰도나 신체 비율 휴리스틱은 사용하지 않습니다.
- `src/inference/sam_reference.py`: 사람 한 명을 검출한 뒤 A 자세 변환 전에 프레이밍 검사를 호출하고, 통과 근거를 요청 임시 NPZ에 저장합니다.
- `src/core/sam_runtime.py` / `src/api/avatar.py`: 상주·단발 실행의 `full_body_required` 입력 오류를 보존해 HTTP 422 재촬영 안내로 전달합니다.
- `src/geometry/sam_avatar_worker.py`: 임시 surface의 검사 근거를 GLB `photo_validation`으로 보존합니다. 실제 메시와 높이 정규화 방식은 유지합니다.
- `../tests/test_photo_visibility.py`: 정상 전신·넓은 팔 자세, 부분 사진·근거 이탈·잘못된 입력과 임계값 경계를 Blender/GPU 없이 검사합니다.
- `../../../deploy/Dockerfile.avatar-source` / `../../../deploy/body-source-update.sh`: 의존성 변경이 없는 기존 VM에서 커밋된 소스만 검증·배포하고 기동 실패 시 이미지·소스를 복원합니다. 모델·환경 파일·역할 권한은 수정하지 않습니다.
- `docs/photo-validation.md`: 프레이밍 검사 범위와 웹 오류 전달, 서버 정상·부분 사진 회귀 및 배포 확인 절차입니다.
