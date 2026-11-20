> Current implementation: Blender runs per request and is not resident. Verified original files stay cached on VM disk. SAM residency is unchanged. Current source is authoritative; earlier versioned modeling notes below are historical.

> Body responses include the three ML girths; failures return null girths. Body jobs use independent object/mesh/shape-key copies. See ../docs/blender-oneshot.md.

# 신체 서비스 파일 연결

| 호출 파일 | 연결 대상 | 전달 내용 |
| --- | --- | --- |
| infra/deploy/body-start.sh → runtime_mode | 상주 모드에서 별도 GPU 모델 검사 생략 | 모델 중복 로딩 방지·API 시작 검증 재사용 |
| api/avatar.py lifespan → core/sam_runtime.py → sam_reference.py serve | 모델 시작 시 로드·요청별 경로 JSON·결과 표식 | 상주 모델 재사용·실패 시 재시작 |
| api/avatar.py → core/error_logging.py | 422·503 및 요청 검증 오류 | 본문 제외 detail 로그 |
| geometry/deform.py → geometry/worker.py → runtime.py | 변형 범위 보정 | fitme_adjustments·applied_target·보정 로그 |
| api/avatar.py → core/photo.py → reconstruct | JPEG/PNG 검증·EXIF 보정·1600만 화소 이하 JPEG | SAM 추론 입력 |
| core/runtime.py → os.memfd_create 또는 /dev/shm TemporaryFile → Blender | 메모리 기반 출력 파일 디스크립터 | 미지원 Python 대체 경로·요청 종료 시 정리 |
| sam_dimensions.py → sam_measure_worker.py → core/features.py | 항목별 단면 실패·숫자 유효성·키 보정 | 정상 cm 또는 null 11개, 전체 메시 오류는 중단 |
| azureml/features.py → score_studio.py | JSON null → 숫자형 NaN | ML 측 결측치 처리 모델에 전달 |
| Dockerfile | MoGe 커밋 925b8ed835a7a9cdb7578ba15c658a0afc969030·constraints-sam.txt | NumPy 1.26.4 고정을 유지하는 MoGe v2 설치 |
| api/avatar.py | core/test_prediction.py·test_measurements.json | example 모드에서 ML 호출 대신 키 비례 예시 치수 제공 |
| compose.ml-free.yaml | avatar 환경변수 | FITME_PREDICTION_MODE=example 선택 |
| geometry/worker.py | GLB scene extras | 예시 결과의 fitme_prediction_source 기록 |
| 웹 web/model_pair.py | api/avatar.py | 사진·실제 키·몸무게·인증 사용자 |
| api/avatar.py | inference/sam_reference.py | SAM 고정 A 포즈 |
| api/avatar.py | core/runtime.render | surface_path·height_cm·sam_avatar_worker.py·가이드 blend |
| sam_avatar_worker.py | sam_measure_worker.load_surface | SAM 정점·SAM 삼각형·투영 부위 가이드 |
| load_surface | sam_body.npz·deform.solve | 기준 가이드 준비 및 좌표계 정렬, 개인 신체 변형 없음 |
| sam_avatar_worker.py | core/sam_surface.py | 신체·가이드 동일 배율 키 보정 및 바닥 정규화 |
| sam_avatar_worker.py | measure.analyze·deform.sections | 앵커·출처별 치수 보고서 |
| sam_avatar_worker.py | GLB sam_geometry.section_diagnostics | 가이드 위치·둘레, 단면 후보 치수·중심 및 선택 중심 |
| sam_avatar_worker.py | geometry/glb.py | SAM 정점·삼각형·앵커 직접 GLB |
| sam_avatar_worker.py | mesh_anchors.extract | 기존 필수 6개와 선택적 목 앵커 2개·측정 어깨 경사 |
| core/runtime.py | storage/blob_assets.py | GLB·앵커·치수 보고서 게시 |
| infra/deploy/body-start.sh | compose.yaml | 신체 API·모델 동기화만 기동 |
| 의류 storage/body_asset.py | body-glb | 소유자/해시로 원본 SAM GLB 읽기, 계산 영역 파생 및 최종 원본 검사 |
| infra/deploy/body-readiness.py | core/ml_endpoint.py | ML 설정은 참고용, 기동 조건에서 제외 |

compose.ml.yaml·로컬 ML FastAPI는 제거했습니다. core 계약과 Azure ML 배포 사본은 동기화 테스트로 비교합니다.


### Body girths and fit judgement API
`core/runtime.render` adds ML male chest/waist/hip girths to successful avatar receipts through `core/body_girths.py`. `core/error_logging.py` preserves failure status/detail/headers and emits null girths for HTTP, validation and unhandled failures on /api/avatars. These are predicted inputs, not post-deformation mesh measurements.


### Resident body Blender with request copies (current)
`api.avatar.lifespan` starts `core.blender_runtime.resident` before SAM and stops both in nested finally blocks. `measure_surface` and `core.runtime.render` use the same resident Blender by default. `geometry.resident_worker` opens FITME_TEMPLATE once, then `template_copy.request_body` deep-copies the object/mesh/shape keys for each measurement or render and removes the copy on success/error. `deform.solve` accepts an optional body object; worker.generate returns GLB bytes without touching the template. Per-request Blender object/mesh/key counts are checked; timeout or cleanup failure kills the process, next request reloads. AVATAR_BLENDER_MODE=oneshot remains a rollback path. Real 175-182-175 GLBs were identical for A/A, source file/key hashes and data counts stayed fixed, a failed request and SAM measurement reused the same process. See docs/resident-blender.md and scripts/test_blender_resident.py.


### Current policy: oneshot Blender, disk model cache only
The API no longer starts or calls resident Blender. Avatar measures SAM surfaces and renders body copies with per-job subprocess.run; SAM inference residency is unchanged. Garment lifespan verifies/downloads model files only, and runtime launches Blender per request. All original cache/Blob paths, center-back shirt and static pants policies stay unchanged. Temporary output descriptors and request copies are cleaned up. Resident helper modules are historical/manual tools, not API paths. See docs/blender-oneshot.md.
기본 사진 API는 기존 predict/measure_surface/geometry.worker.py를 호출하지 않습니다.
기존 ML 계약은 별도 호환 도구로 유지하며 배포 사본 동기화 검사를 유지합니다.

### 전신 사진 검사와 오류 전달

원본 사진의 shape + SAM 사람 결과(bbox, MHR70 `pred_keypoints_2d`) → `core/photo_visibility.validate_full_body` → 통과한 정규화 프레이밍 수치 또는 안전한 `PhotoFramingError.reason`.

`inference/sam_reference.infer_photo`의 A 자세 변환 전 검사 → `InputError(code='full_body_required')` → 상주 JSON 응답 또는 단발 `FITME_INPUT_ERROR` → `core/sam_runtime.SAMInputError` / `api/avatar.reconstruct` → HTTP 422 재촬영 안내. 통과 수치 → surface NPZ `photo_validation_json` → `geometry/sam_avatar_worker.build_avatar` → GLB scene extras `photo_validation`.

`../tests/test_photo_visibility.py` → 순수 NumPy helper: 상하/좌우 잘림·투영 영역 이탈·검출 영역 밖 추정·근거 누락·경계 임계값을 검사하고 넓은 A 자세는 비율 제한 없이 통과시킵니다. 이 경로는 관측 visibility confidence나 완전한 가림 검사를 추가하지 않습니다.

HTTP 422 `detail.code` → 웹 `web/model_pair.generate`의 알려진 오류 안내 → `generate_pair` 신체 실패 시 의류 요청 중단 → 촬영 화면 오류 표시. `web/static/fit-room.js`는 준비 확인을 기다리며 실제 촬영 실패를 예시 신체·근사 옷으로 전환하지 않습니다.

Git 커밋별 `src/`·manifest → `infra/deploy/body-source-update.sh` → `infra/deploy/Dockerfile.avatar-source`와 기존 로컬 런타임으로 오프라인 빌드 → API/SAM import·해시 검사 → avatar 단독 교체 → `/health` revision 및 실행 소스 해시 검사. 실패 시 이전 이미지·호스트 소스를 복원하며 모델 동기화 서비스는 호출하지 않습니다.
