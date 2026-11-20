> Current implementation: Blender runs per request and is not resident. Verified original files stay cached on VM disk. SAM residency is unchanged. Current source is authoritative; earlier versioned modeling notes below are historical.

> Body responses include the three ML girths; failures return null girths. Body jobs use independent object/mesh/shape-key copies. See ../docs/blender-oneshot.md.

# 신체 서비스 아키텍처

예측 치수가 변형 가능 범위를 벗어나면 rise_arc_cm은 로컬 변형 양 끝 중 가까운 경계로 보정합니다.
단일 너비/두께와 둘레가 충돌하면 둘레로 가능한 한계의 99.99%까지 줄여 퇴화 단면을 피합니다.
신체 기준 높이는 키를 고정한 채 최소 1.5cm 간격을 유지하도록 순서대로 보정합니다.
알 수 없는 필드·비유한/음수 값·잘못된 자세·기준 메시 손상은 계속 오류로 처리합니다.
GLB fitme_adjustments와 치수 보고서 applied_target에 보정값을 남기며 target은 원래 ML 값을 유지합니다.
abs_error는 원래 ML 값 대비 최종 메시 차이입니다. 보정은 생성 성공을 위한 것이며 치수 정확도를 보증하지 않습니다.

API lifespan에서 별도 GPU Python의 sam_reference.py serve 프로세스를 시작하고 모델을 한 번 로드합니다.
요청마다 사진·출력 경로만 stdin JSON으로 전달하고 stdout 완료 표식을 받아 기존 Blender 단계를 진행합니다.
한 명 미검출 오류는 프로세스를 유지하고, 시간 초과·프로세스 종료·통신 오류는 정리 후 다음 요청에서 재시작합니다.
SAM_RUNTIME_MODE=oneshot은 기존 요청별 실행으로 되돌리는 옵션이며 기본값은 resident입니다.
상주 모드는 시작 시 GPU 모델 로드 시간과 GPU 메모리를 사용합니다. 실제 VM 지연시간은 별도 측정해야 합니다.

422·503 응답은 서버 로그에 method·path·detail을 기록합니다. 검증 오류는 필드·오류 종류만 기록하며
사진·요청 본문·인증 헤더·쿼리·서명 URL은 로그에 넣지 않습니다. 보정 내역도 FITME_ADJUSTMENT로 기록합니다.

사진은 3MiB 이하 JPEG/PNG를 받고 원본 최대 6400만 화소까지 허용합니다. core/photo.py가
EXIF 방향을 보정하고 비율을 유지해 최대 1600만 화소로 축소한 JPEG를 SAM에 전달합니다.
픽셀 디코딩은 job_slot 획득 후 스레드에서 수행해 동시 디코딩을 제한하며 원본을 영구 저장하지 않습니다.
Blender 출력은 os.memfd_create를 우선 사용하고 미지원 또는 호출 실패 시
tempfile.TemporaryFile(dir='/dev/shm')로 전환합니다. 파일 디스크립터 전달·자동 정리는 동일합니다.

SAM 입력 11개는 항목별 결측치 `null`을 허용합니다. 단면 탐색 실패는 해당 항목만 결측 처리하고,
좌우 평균 항목은 양쪽이 모두 측정됐을 때만 값을 사용합니다. 샅점 실패는 샅높이·엉덩이 4개·넓적다리둘레에 전파됩니다.
0·음수·비수치·비유한값·1000cm 이상 값, 키 이상인 샅높이·엉덩이 너비/두께/높이는 null입니다.
신체 전체 메시·바인딩 불일치, 키 보정 불가는 요청을 중단합니다. 누락 필드 자체는 계약 오류입니다.
11개 모두 null이어도 유효한 키·몸무게와 함께 전달하며, 대체값 예측은 ML 모델이 담당합니다.
Studio score는 JSON null을 숫자형 NaN으로 변환하므로 ML 모델은 결측치 처리 또는 학습된 imputer를 포함해야 합니다.
임의 정상 체형 범위 판정이나 기본 템플릿 값 대체는 하지 않습니다. ML 출력 28개는 여전히 null을 거절합니다.

Dockerfile의 MoGe 설치 커밋은 `925b8ed835a7a9cdb7578ba15c658a0afc969030`으로 고정합니다.
`moge.model.v2`·`moge-2-vitl-normal`을 사용하는 SAM 깊이 추정 경로를 유지하며,
`constraints-sam.txt`의 NumPy 1.26.4 고정과 충돌하는 MoGe V3 설치를 피합니다.

ML 없는 테스트는 `FITME_PREDICTION_MODE=example` 또는 `compose.ml-free.yaml`로 선택합니다.
사진→SAM 복원·측정은 유지하고 `predict`에서 ML 인증·HTTP 요청·응답 대신
키 175cm 기준 예시 28개를 입력 키에 비례해 조정합니다. 몸무게·SAM 치수로 체형을 예측하지 않습니다.
결과 GLB scene extras의 `fitme_prediction_source=example`로 테스트 결과를 구분합니다.
기본 `azure_ml` 경로와 실패 처리는 유지하며, ML 실패 시 예시값으로 자동 대체하지 않습니다.
웹 응답에는 `body.measurements_url`을 포함합니다. 실행법은 `../ML_FREE_TEST.md`를 참조합니다.

현재 구성은 A 방식입니다. 신체 VM의 avatar API → Azure ML 관리형 실시간 엔드포인트 → 신체 VM의 기본 모델 변형 흐름입니다. 같은 VM의 ml 서비스는 제거했습니다.
기본 사진 API는 SAM이 복원한 A 자세 메시를 직접 GLB로 저장합니다.
사진 → inference/sam_reference.py → surface.npz → geometry/sam_avatar_worker.py → body-glb입니다.
Azure ML의 28개 치수로 기본 신체를 변형하는 단계는 이 API에서 호출하지 않습니다.
대신 `FITME_ML_MEASUREMENTS=on`(기본 off)이면 `api/avatar.py`의 `ml_prediction`이 SAM 측정 11개와 키·몸무게를 Azure ML에 보내고, 받은 28개를 치수 보고서의 `target`(핏 판정용)으로만 붙입니다. SAM 메시는 변형하지 않으며, ML 호출이 실패하면 `target`은 비고 웹은 `measured`로 판정합니다. `FITME_PREDICTION_MODE=example`의 예시 치수는 핏 판정에 쓰지 않습니다.

sam_measure_worker.load_surface()는 기존 보정 자산으로 좌표계를 맞추고 기본 모델의 측정 가이드를 SAM 표면에 투영합니다.
실제 정점과 삼각형 연결은 SAM에서 유지합니다. 기본 blend는 부위/앵커 가이드에만 사용합니다.

core/sam_surface.py는 실제 키 / SAM 높이의 동일 배율을 세 축과 투영 가이드에 적용하고 바닥을 0으로 옮깁니다.
몸무게는 기존 요청 호환을 위해 받지만 메시 확대에는 사용하지 않습니다.
fit_neck_L/R도 투영된 목 랜드마크에서 내보내 의류의 초기 어깨 경사 정렬에 사용합니다.
목 앵커는 선택적 추가 항목이며 기존 필수 앵커 6개 계약을 유지합니다.

측정 보고서에서 높이는 실제 SAM 메시, 가슴·허리·엉덩이는 투영 기준 높이의 실제 수평 단면입니다.
그 외 치수/앵커는 투영 가이드 기반 근사값이며 surface 필드로 구분합니다.
단면을 찾지 못하면 투영 가이드 값임을 표시하고 measurement_diagnostics에 남깁니다. 측정 위치 정확도 검증은 별도로 필요합니다.

`sam_geometry.section_diagnostics`에는 가슴·허리·엉덩이별 가이드 위치와 둘레, 실제 단면 후보의 둘레·너비·두께·중심, 선택된 단면 중심을 함께 저장합니다. 단면이 없으면 unavailable로 기록합니다. 가이드 높이와 후보 선택이 판정용 둘레에 미치는 영향을 서버 GLB에서 확인하기 위한 정보이며 측정값 계산은 바꾸지 않습니다.

GLB의 body_geometry_source와 /health에 sam_surface를 표시합니다. GLB·앵커·측정 보고서 URL 계약은 유지합니다.
의류 VM은 이 GLB에서 계산 영역을 선택·단순화하되 표시 신체는 변경하지 않습니다.
충돌 계산은 파생 메시를 사용하고 최종 관통 검사는 이 원본 SAM 전체를 기준으로 합니다.

기존 features.py·ML 호출 보조 함수·geometry/worker.py는 별도 호환 도구로 남아 있습니다.
원격 ML 설정은 신체 API 기동 조건이 아닙니다. SAM 체크포인트·A 자세·바인딩·가이드 blend는 계속 필요합니다.

Blender tests/blender_sam_avatar.py는 원래 SAM 정점·삼각형 유지와 동일 배율 키 보정·앵커를 검사합니다.
GPU/Blender 실사진 실행 검증은 별도로 수행해야 합니다.

원본 네 파일은 SAM 추론·측정 가이드·기본 모델 변형에 계속 필요합니다. 사진과 중간 입력은 VM 요청 메모리에서 처리하며 SQL 중계는 없습니다. 웹 FastAPI의 기존 요청·결과 링크 계약은 유지합니다. 실제 Azure ML 리소스 생성과 VM 배포는 이번 코드 변경에서 수행하지 않았습니다.


### Body girths and fit judgement API
`core/runtime.render` adds ML male chest/waist/hip girths to successful avatar receipts through `core/body_girths.py`. `core/error_logging.py` preserves failure status/detail/headers and emits null girths for HTTP, validation and unhandled failures on /api/avatars. These are predicted inputs, not post-deformation mesh measurements.


### Resident body Blender with request copies (current)
`api.avatar.lifespan` starts `core.blender_runtime.resident` before SAM and stops both in nested finally blocks. `measure_surface` and `core.runtime.render` use the same resident Blender by default. `geometry.resident_worker` opens FITME_TEMPLATE once, then `template_copy.request_body` deep-copies the object/mesh/shape keys for each measurement or render and removes the copy on success/error. `deform.solve` accepts an optional body object; worker.generate returns GLB bytes without touching the template. Per-request Blender object/mesh/key counts are checked; timeout or cleanup failure kills the process, next request reloads. AVATAR_BLENDER_MODE=oneshot remains a rollback path. Real 175-182-175 GLBs were identical for A/A, source file/key hashes and data counts stayed fixed, a failed request and SAM measurement reused the same process. See docs/resident-blender.md and scripts/test_blender_resident.py.


### Current policy: oneshot Blender, disk model cache only
The API no longer starts or calls resident Blender. Avatar measures SAM surfaces and renders body copies with per-job subprocess.run; SAM inference residency is unchanged. Garment lifespan verifies/downloads model files only, and runtime launches Blender per request. All original cache/Blob paths, center-back shirt and static pants policies stay unchanged. Temporary output descriptors and request copies are cleaned up. Resident helper modules are historical/manual tools, not API paths. See docs/blender-oneshot.md.
사진과 중간 surface는 요청 임시 디렉터리에서 처리하며 렌더링이 끝난 뒤 삭제합니다. SQL 중계는 없습니다.

### 전신 사진 프레이밍 검사

`inference/sam_reference.infer_photo`는 사람 한 명을 검출한 뒤, 고정 A 자세로 바꾸기 전에 `core.photo_visibility.validate_full_body`로 원본 사진 픽셀 좌표의 bbox와 MHR70 예측 투영 좌표를 검사합니다. bbox가 각 이미지 변에서 `max(2px, 해당 변 길이의 0.3%)`보다 가깝거나, 머리·몸통·양팔/손목·다리·양발의 필수 23개 점이 이미지 밖 1%를 넘거나 검출 상자에서 bbox 높이 6%를 넘게 벗어나면 거절합니다. 키포인트의 순서·크기·유한 숫자와 이미지 크기를 확인하며 누락된 근거를 검사 생략으로 처리하지 않습니다. 몸통의 세로/가로 비율이나 신체 치수로 전신 여부를 추측하지 않습니다.

거절은 안전한 사유 코드의 `PhotoFramingError` → SAM `InputError(code='full_body_required')` → 상주/단발 실행 통신 → HTTP 422의 정적 전신 재촬영 안내로 전달합니다. 실패 사진의 GLB는 생성하지 않습니다. 통과한 정규화 프레이밍 수치는 요청 임시 surface NPZ의 `photo_validation_json`과 결과 GLB의 `photo_validation`에 보존합니다. 사진 픽셀이나 경로는 보고서에 포함하지 않습니다.

이 검사는 예측 신체의 프레이밍과 사람 검출 영역의 지지 여부를 확인합니다. SAM의 `pred_keypoints_2d`는 관측 신뢰도가 포함된 2D 검출 결과가 아니라 예측 3D의 투영이며 독립 visibility confidence는 제공되지 않습니다. 따라서 물체에 가려진 신체나 이미지 안에 그럴듯하게 추정된 모든 미관측 부위를 검출한다고 보장하지 않습니다. 임계값은 서버의 정상 전신·잘린 사진 회귀로 검증해야 합니다.

웹 `web/model_pair.generate`는 알려진 사진 오류 코드만 정적 재촬영 안내로 변환합니다. 신체 오류이면 의류 요청을 중단합니다. 촬영 화면은 3D 연결 확인을 기다리고, 일반 모드의 연결·의류 오류를 예시 신체나 근사 옷으로 대체하지 않습니다.

소스 전용 배포는 `infra/deploy/Dockerfile.avatar-source`와 `infra/deploy/body-source-update.sh`를 사용합니다. 커밋별 소스 manifest와 기존 로컬 GPU 런타임을 검증한 뒤 avatar 컨테이너만 교체하며 모델·환경 파일을 유지합니다. `/health`의 `source_revision`으로 실제 실행 커밋을 확인합니다. 배포와 검증 절차는 `../docs/photo-validation.md`를 참조합니다.
