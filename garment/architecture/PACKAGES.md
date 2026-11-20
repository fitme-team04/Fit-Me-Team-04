> Current implementation: Blender runs per request and is not resident. Verified original files stay cached on VM disk. SAM residency is unchanged. Current source is authoritative; earlier versioned modeling notes below are historical.

> body_model_id가 있는 현재 피팅은 실제 SAM 단면으로 의류 사본을 맞추며 상품 DB 실측을 크기 입력으로 사용하지 않습니다. 신체 없는 생성은 상의 garment.measures·하의 고정 원형 경로를 유지합니다. 템플릿은 body_center_back_v19와 black_midrise_straight_v1입니다. 현재 SAM 정책은 아래 현재 피팅 절과 ../docs/sam-body-fitting.md를 참조합니다.

# 파일 역할

`build_body_proportional_shirt.py::refine_style`: v14 고정 비율 스타일 수선. 허리 2.5% 안쪽 보정, 어깨/팔 평활화와 소매 테이퍼, 신체를 침범하는 이동 차단.
`build_body_proportional_shirt.py::rebuild_clean_sleeves`: 팔 단면 중심을 기준으로 소매를 연속 테이퍼 면으로 다시 이어 근육 돌출이 덜 드러나도록 정리.

`scripts/build_body_proportional_shirt.py`: 인체 표면에서 어깨·팔을 이어받고 4개 상의 치수와 고정 비율만으로 생성하는 v13 도구. 기존 투영/케이지 임의 변형은 사용하지 않음.

`scripts/rebuild_smooth_shirt.py`: 어깨·소매를 단일 연결 표면으로 합치고 배 돌출 없는 윤곽과 약간 좁은 밑단을 만드는 v12 수선 도구.

`scripts/repair_tripo_shirt.py`: v10 상의의 연결면을 재구성해 소매와 밑단을 정리하고 원본 재질을 대응시키는 자산별 수선 도구.

| Tripo 체형 대응 파일 | 역할 |
| --- | --- |
| `scripts/prepare_tripo_fit_sources.py` | 원본 보존, 방향 정규화, UV를 유지한 작업 사본 경량화 |
| `scripts/open_tripo_ports.py` | 광선 검사로 확인한 내부 막힘을 작업 사본에서 제거해 목·손목·허리·밑단 통로 확보 |
| `../avatar/scripts/build_fit_test_bodies.py` | 실제 신체 변형기로 29개 치수 변형용 합성 체형 생성 |
| `src/geometry/body_clearance.py` | 신체 삼각형 대응, 체형 변형량 추종, 관통 검사 실패 출력 차단 |
| `scripts/test_tripo_fit_matrix.py` | 상의 4개·하의 7개 치수와 체형 행렬의 보정·검증·결과 기록 |
| `scripts/fit_body_garment.py` | 실제 신체 NPZ와 의류 spec JSON의 단건 체형 추종·충돌 보정·검증 후 GLB 출력 |
| `scripts/verify_tripo_exported.py` | 전달 GLB를 별도 Blender 프로세스에서 재수입해 관통·UV·질감 검사 |
| `scripts/project_garment_surface.py` | 발등/바닥 관통 보호, 국소 세분화와 UV 보존 투영. 원래 상품 치수와 최종 형상 차이는 검토 필요 |

`scripts/fit_shirt_hem.py`: 비교 장면의 바지를 제거하고 상의 밑단을 신체 허리에 맞추는 독립 도구.

`place_original_garments.py`의 `--width-only` 선택지는 어깨·허리 너비만 국소 조정하며 길이·두께 불변을 검사합니다.

`scripts/place_original_garments.py`: 원본 의류를 어깨·허리 높이로 평행 이동하고 크기·메시·회전 불변을 검사하는 독립 비교 도구.


`src/database/connection.py`는 의류 VM의 SQL 연결과 관리 ID 인증을 처리합니다.
`architecture/install-odbc.sh`는 의류 Docker 이미지 내부에 드라이버를 설치합니다. 로컬 설치 도구는 제공하지 않습니다.

| 파일 | 역할 |
|---|---|
| `scripts/fit_uploaded_garments.py` | 사용자 제공 질감 의류 GLB의 기준 신체 대응·소매 A 자세·원본 UV 보존 및 v6 등록. 신체 충돌만 보정하고 상하의 상호 충돌 계산은 생략 |
| `scripts/build_reference_wide_slacks.py` | 벨트 없는 회색 와이드 팬츠·허리와 바지통 재구성 및 기존 반팔과의 검증 |
| `scripts/build_reference_tshirt.py` | 참고 이미지 스타일의 흰색 크루넥 반팔·봉제선·주름 모델링 및 기준 착장 적용 |
| `scripts/repair_reference_outfit.py` | 상의 옆구리·밑단 재구성과 바지 상부 조정·등록 |
| `scripts/check_reference_outfit.py` | 최종 GLB 상·하의 교차 및 간격 검증 |
| `scripts/convert_reference_templates.py` | GLB 중계로 배포 Blender 버전에서 모델 저장·바인딩 재생성 |
| `scripts/rebuild_cc0_reference.py` | 기준 신체에 CC0 의류 정렬·관통 보정·원본과 분리한 v2 생성 |
| `scripts/verify_reference_garments.py` | 서비스 경로의 실제 GLB를 재수입해 충돌과 기준점 검증 |
| `src/core/frame_watch.py` | 프레임 시작·완료와 프레임별 제한시간을 추적합니다. |
| `src/core/blender_process.py` | Blender 실행·로그와 외부 프레임 감시·종료를 담당합니다. |
| `src/core/pose_geometry.py` | 3D 각도·목 등록·DB 치수 보존·닫힌 신체 면 방향을 검사합니다. |
| `src/geometry/garment_pose.py` | SAM 랜드마크로 목·어깨·소매 초기 자세 후보를 Blender Armature로 만듭니다. |
| `src/core/cloth_geometry.py` | SAM 영역 선택과 국소 보정의 DB 크기·면 방향 한계를 검사합니다. |
| `src/core/frame_watch.py` | 프레임 시작·완료 이벤트와 프레임별 제한시간을 추적합니다. |
| `src/core/blender_process.py` | Blender 자식 실행·로그 중계·외부 프레임 감시와 종료를 담당합니다. |
| `src/geometry/collision_proxy.py` | 표시 원본을 유지하고 SAM 선택 영역의 계산용 단순화를 검사·적용합니다. |
| `scripts/check_cloth_preprocess.py` | 합성 Blender 메시로 충돌 전처리와 원본 기준 키 보존을 검증합니다. |
| `src/core/cloth_checkpoint.py` | 중단된 작업의 완전한 GLB 메시를 유지하고 실패 원인을 추가합니다. |
| `src/core/cloth_contract.py` | 전체 옷 질량을 정점 질량으로 변환하고 Cloth 결과의 엣지·안정성·관통 한계를 검사합니다. |
| `src/storage/body_asset.py` | 소유자별 신체 GLB를 읽고 크기·해시를 검증합니다. |
| `src/geometry/cloth_fit.py` | DB 실측 옷을 실제 신체에 Cloth + Collision으로 시뮬레이션하고 최종 메시로 확정합니다. |
| `src/api/garments.py` | 실상품·사이즈 조회와 선택 의류의 GLB 생성 API를 제공합니다. |
| `src/checks/check_db.py` | 실상품·측정 별칭 테이블과 category 컬럼을 확인합니다. |
| `src/core/catalog_mapping.py` | category를 종류·템플릿에 연결하고 출처별 소매 측정 기준을 해석합니다. |
| `src/checks/check_generation.py` | Blender와 기본 의류 템플릿의 GLB 생성 결과를 검사합니다. |
| `src/core/contract.py` | 신체 치수 입력 계약과 서버가 정한 고정 자세를 검증합니다. |
| `src/core/garment_specs.py` | 의류 종류별 필수 실측 코드·범위·측정 기준을 검증합니다. |
| `src/core/runtime.py` | Blender 작업을 실행하고 생성된 GLB를 결과 Blob에 게시합니다. |
| `src/database/connection.py` | 환경변수로 Azure SQL 연결을 구성하고 쿼리·트랜잭션을 수행합니다. |
| `src/geometry/garment_cages.py` | 상의·하의 변형의 기준이 되는 케이지 형상을 만듭니다. |
| `src/geometry/garment_worker.py` | Blender에서 등록 의류를 실측에 맞춰 변형하고 GLB로 내보냅니다. |
| `src/geometry/glb.py` | GLB 바이너리를 구성·해석하고 메시와 앵커를 내보냅니다. |
| `src/geometry/mesh_anchors.py` | GLB에서 신체·상의·하의 정렬 앵커와 피팅 메타데이터를 읽습니다. |
| `src/geometry/slacks.py` | 슬랙스 기준 형상과 치수별 변형을 계산합니다. |
| `src/geometry/template_binding.py` | 등록 의류 메시와 케이지를 연결하고 정점 변형을 적용합니다. |
| `src/geometry/template_catalog.py` | 템플릿 ID를 모델·바인딩 경로에 연결하고 등록 정보를 검사합니다. |
| `src/storage/blob_assets.py` | 생성 결과를 비공개 Blob에 저장하고 사용자별 다운로드 URL을 발급합니다. |


### v15 shoulder and sleeve refinement
`build_body_proportional_shirt.py` applies a 5.5% local waist inset and a straight sloping shoulder roof. `rebuild_clean_sleeves` uses a convex radial envelope to fill sleeve dents. The four-input contract remains unchanged; body-intersection validation is required before registration.


### v16 upper sleeve only
After continuous sleeve reconstruction, the builder fills proximal upper-sleeve concavities toward the convex x/z silhouette. Correction fades to zero at the arm axis; lower sleeve vertices and waist are unchanged. Final body and topology checks remain required.


### v17 hem side taper
The builder narrows only the lateral bottom edges by up to 2.5%, fading over the lowest 14% of garment length. Front/back depth, upper waist and sleeves remain unchanged. Final body-intersection checks gate registration.


### v18 lower abdomen silhouette
After hem taper, the builder clamps the lower torso lateral silhouette to a straight tapered envelope. Exact body intersection checks still gate export. Sleeves and upper torso remain unchanged.


### Approved shirt Blob release packaging
`scripts/package_shirt_release.py` reads an approved release and its delivered GLB validation, then bundles model/NPZ/registry, four-input JSON, reference body, regeneration code, architecture diagrams and SHA-256 manifest. `docs/shirt-blob-release.md` documents the upload layout and offline regeneration policy. This packaging step does not upload blobs or enable API regeneration.


### Reference black pants preview
`scripts/preview_reference_pants.py` loads the intact v5 scene, hides the shirt, gently tapers lower leg width, applies body clearance and validates intersections before rendering front/side/angle previews and saving a separate scene. The damaged Tripo pants and approved shirt release are unchanged. This is a local style preview, not a deployed template.


### Mid-rise pants preview
`preview_reference_pants.py --mid-rise` lowers the waistband by 3cm, maps its width/depth to the body section at that height with 5mm radial ease, blends over the upper 18cm, then applies body-clearance checks and exports a separate GLB and previews. Original pants and the approved shirt are preserved.


### Mid-rise hip refinement
`preview_reference_pants.py --mid-rise --slim-hips` samples trouser cross-sections and reduces excess lateral hip width with a continuous height-dependent scale, preserving the waistband and lower legs. Body-clearance correction and intersection checks precede preview and GLB export into a separate output directory.


### Straight calf silhouette
`preview_reference_pants.py --mid-rise --slim-hips --straight-calves` adds section-based lateral narrowing from upper leg to hem, removing lower-leg flare while retaining mid-rise and waist settings. It validates body clearance and writes a separate straight-pants scene, GLB and previews.


### Service pants registration and package
`register_reference_pants.py` transforms the approved world-space pants into the actual body waist-anchor frame, then registers black_midrise_straight_v1 BLEND/NPZ/registry. `verify_reference_garments.py` validates baseline worker export against the body. `check_pants_size_controls.py` exercises each of seven cage inputs at +0.5cm and verifies finite changed mesh output. `docs/pants-blob-release.md` documents Blob deployment, remaining category mapping and cage-versus-surface measurement limits.


### Final release consolidation
The canonical approved shirt/pants assets and editable fitting scenes are in `releases/final-garments`. Duplicate upload bundles and intermediate pants previews were removed after hash verification. `check_pants_size_controls.py` now reads the canonical models and writes new smoke outputs to `.cache/pants-size-checks`. Original Tripo sources, v5 pants regeneration input and Blender tooling are retained.


### Approved category mapping
`category_template` maps upper garments to body_proportional_shirt_v18 and lower garments to black_midrise_straight_v1. `generation_settings` retains source-specific sleeve basis. `GARMENT_TEMPLATE_DIR` must reference the downloaded final models directory; old default registries do not contain these IDs. VM configuration and Docker model provisioning remain separate deployment steps.


### Shape-preserving shirt policy v18.1 (current)
`template_binding.deform` validates the registered binding, then calls `shirt_shape.reshape` for four-input region-aware deformation. `protect_reference_body` uses body arrays embedded in the updated NPZ and limits corrections to 8mm; residual penetration, new self-overlap candidates and inverted/collapsed triangles are rejected. Shoulder-based input only, 90..110 percent size range. This supersedes the former regeneration-only shirt policy. `check_shirt_shape.py` covers 21 cases (10 clear generated, 11 safely rejected), and `check_shirt_worker.py` reimports and renders four actual service GLBs. Three inherited neckline overlap candidates remain; different bodies and combined outfit collisions are not covered.


### Current export policy v18.2 (supersedes collision guards above)
User-requested anchor-based export: `template_binding.deform` applies size deformation and writes anchors without body projection, body-reference requirements or collision-based rejection. `shirt_shape.py` no longer contains body correction or self-crossing functions. Numeric/input integrity and collapsed/inverted-face validation remain. Offline checks report collisions diagnostically; 21 of 21 size cases export, including penetrating cases.


### Body girths and fit judgement API
`api.garments` includes `api.fit.router`: POST /fit reads all product sizes using ease_check.MEASURES_SQL, calls sizes_from_db_rows then check_all_sizes unchanged. A catalog query includes sizes without measurements as UNDETERMINED. Module src/ease_check.py comes from origin/feature/ease-check e201b59 and is included by existing Docker COPY src. Existing ingress subject authentication applies. selected contains verdict/message_ko/parts.


### Slacks four-input contract (current)
`garment_specs.validate_spec` requires only waist_width/hip_width/thigh_width/inseam. `api.garments` ignores other DB codes. `complete_slacks_spec` derives rise from registered rise/hip ratio and knee/hem from registered leg-width ratios; `template_binding.deform` uses the NPZ baseline and holds the waist anchor fixed. Worker reports only four supplied metrics plus clearly labeled derived_proportions_cm. `prepare_template.register` keeps the full internal cage baseline in NPZ while publishing four input settings. No body collision correction is added. See docs/slacks-four-inputs.md.


### Live SQL catalog integration (2026-11-16)
Read-only Azure CLI Entra/.NET inspection confirmed 6 demo products/42 size rows only in garment.size_musinsa_standard/size_topten/size_ziozia, absent from normalized product IDs. `database/brand_catalog.py` reads allowlisted tables and maps girths to half-widths. `api.garments` adds brand-catalog discovery and item_code+exact size_label generation fallback; legacy numeric IDs remain unchanged. `api.fit` shares the adapter for all-size fit assessment. Product notes preserve calculated inseam provenance. No top body_length column exists for these products; generation remains a clear missing-field error. All 134 aliases confirm uniqlo_site uses sleeve-length-cb (center-back), requiring separate conversion for the shoulder-only shirt template. See docs/sql-catalog-integration.md. SQL/identity/network resources were not modified.

### Reverted picture-based conversion; verified UNIQLO storage
Picture-derived F-to-G estimation and its module/tests/generated artifacts were canceled. Shirt handling is restored to shoulder-only; raw SQL values and source aliases remain unchanged. Live SELECT joins confirm UNIQLO garment-basis measures for 13 products/116 sizes/457 rows: body_length 116, chest_width 116, garment_shoulder_width 109, sleeve_length 116. Body-basis recommended measurements are distinct. Missing total lengths previously reported concern the three brand-table demo tops, not UNIQLO.


### Current generation policy: normalized tops and static pants
Tops use only garment.measures via the normalized product/size join; no brand-top fallback for selection, generation or /fit. Brand fallback queries explicitly filter category=bottoms, and brand-catalog exposes only the 3 pants products. Slacks worker skips product size validation and uses static_template: unchanged mesh, fixed waist/crotch/hem anchors, empty size report and deformation_applied=false. /fit still uses real garment measurements independently of static geometry. `checks.check_generation` handles the empty static report. Current tests: check_static_slacks.py and test_garment_generation_policy.py; earlier proportional slacks tools/results are historical.


### Blob-pinned native center-back models and resident Blender (current)
Mapping uses body_center_back_v19 plus static black_midrise_straight_v1. Native center-back sleeve parameterization is registered in releases/blob-v19 without changing the source shape or SQL. `api.garments.lifespan` calls `storage.model_cache.ensure_models` once, pins file sizes/SHA-256/ETags, selects an immutable disk cache, then starts `core.garment_resident`. `geometry.resident_worker` preloads 2 BLEND meshes and 2 NPZ bindings; garment_worker copies cached originals per request and preserves them. Registry reads are cached too. Runtime GLB generation uses the resident IPC protocol and existing publication. Docker bundles only the trusted manifest; Compose uses a writable persistent cache. Upload received 403; user selected manual ZIP upload. See docs/blob-resident-models.md.


### Container-root model upload
User uploaded models directly into garment-models. The pinned manifest now uses an empty blob_prefix; model_cache joins root filenames without a leading slash. File hashes are unchanged. Remote listing was denied by the current CLI identity, so actual uploaded contents were not verified.


### Current policy: oneshot Blender, disk model cache only
The API no longer starts or calls resident Blender. Avatar measures SAM surfaces and renders body copies with per-job subprocess.run; SAM inference residency is unchanged. Garment lifespan verifies/downloads model files only, and runtime launches Blender per request. All original cache/Blob paths, center-back shirt and static pants policies stay unchanged. Temporary output descriptors and request copies are cleaned up. Resident helper modules are historical/manual tools, not API paths. See docs/blender-oneshot.md.
## 메시 검사 모듈

- src/core/mesh_quality.py: 표준 라이브러리로 삼각형 교차·공면 겹침·면적·토폴로지 검사.
- src/geometry/mesh_validation.py: Blender mathutils BVH 후보, 자기 교차 및 실제 SAM 표면 검사. 추가 pip 의존성 없음.
- src/core/pose_geometry.py: 소매 각도/어깨 위치 오차와 강체 이동 후 glTF 랜드마크 동기화.
- scripts/check_cloth_preprocess.py: Blender의 실제 BVH 교차 및 자세 오차 회귀 검사 포함.
## 초기 겹침 복구 추가

- src/core/cloth_geometry.py: relax_contacts로 이웃에 접촉 보정을 분산하며 DB 길이와 최대 이동을 제한합니다.
- src/geometry/cloth_fit.py: 겹침만으로 조기 종료하지 않고 박힌 고정점을 해제한 뒤 중력 없는 12프레임 복구와 정상 중력 계산을 수행합니다.
- scripts/check_overlap_recovery.py: 실제 Blender 전용 합성 관통 복구 회귀 검사. 추가 의존성 없음.

## 자기 충돌 해상도 모듈

- src/core/cloth_resolution.py: 짧은 모서리·fan 삼각형의 최소 고도에 따른 한 겹 연결 영역과 optional near_faces polygon ID로 제외 정점을 계산하고 좌표·인덱스를 검증합니다. altitude_seed_faces 통계를 반환하며 표준 라이브러리만 사용합니다.
- src/geometry/cloth_self_collision.py: Cloth 전 기준 형태를 fan 삼각형으로 대응해 KDTree 구면·AABB 후보와 정확한 삼각형 간 거리를 계산합니다. 현재 SAM 경로의 기준은 크기 조정 후 rest이며 준비 시간·후보 수 제한과 Blender 그룹·실제 충돌 거리 설정을 담당합니다.
- src/geometry/cloth_fit.py: 설정 완료 보고서를 기록하고 미완료 시 실패 미리보기를 저장합니다. 전체 메시의 최종 검사는 유지합니다.
- ../tests/test_cloth_resolution.py: Blender 없이 근접 face·짧은 모서리·3D/fan 최소 고도의 제외 규칙 및 잘못된 입력을 검사합니다. 추가 의존성 없음.

## 소매 정렬 기하

- src/core/pose_geometry.py::sleeve_target_on_arm: 의류 소매 길이를 유지하면서 SAM 어깨→손목 선분 위의 목표점을 구하는 순수 기하 계산입니다.
- src/geometry/garment_pose.py::articulate: 어깨 보정 후 해당 목표점으로 Blender Armature의 소매 회전을 설정합니다.
- ../tests/test_initial_pose.py: 구면·팔 선분 교점과 길이 보존의 회귀 검사를 포함합니다. 추가 의존성 없음.

## SAM 크기 프로파일 보조 모듈

- src/core/sam_sizing.py: 방사 비율의 tanh 제한과 동일 차원 프로파일 보간을 수행합니다. DB 치수를 받지 않으며 표준 라이브러리만 사용합니다.
- ../tests/test_sam_sizing.py: 반지름 윤곽·프로파일 보간 및 입력 검증을 Blender 없이 검사합니다. 추가 의존성 없음.

## SAM 피팅 원형 준비

- src/api/garments.py: body_model_id가 있으면 상품 치수 없이 category의 등록 템플릿을 선택하고 빈 spec을 전달합니다.
- src/geometry/template_binding.py::body_template: 상의·하의 원형 정점과 등록 anchor reference를 유지하며 해시·바인딩·메시 품질을 검사합니다.
- src/geometry/garment_worker.py: SAM 경로에서 body_template을 사용하고 새 fitting_mode 및 body_sizing 기록을 내보냅니다. 신체 없는 기존 DB 상의·고정 하의 경로도 지원합니다.
- src/core/body_sections.py: 임의 평면·수평 단면의 연결 성분을 별도 닫힌 윤곽으로 구성합니다. 몸통 중심을 가로지르는 윤곽과 팔축 근처의 독립 팔 윤곽을 선택하며 과대 팔 윤곽·열린 성분을 거절합니다. NumPy를 사용하며 Blender 의존성은 없습니다.
- src/core/arm_profiles.py: 안정적인 단면 두 축, 다각형 면적 중심·offset·enclosing 반경 및 convex hull 지지 직선 offset의 64각도 방사 프로파일을 계산합니다. 주기 방향별 표 보간을 제공하고 원래 윤곽·표본 목표 다각형·정확 miter 다각형의 둘레를 구분합니다. NumPy를 사용합니다.
- src/geometry/sam_sizing.py: 닫힌 몸통·독립 팔 단면으로 의류 크기를 조정합니다. 몸통 단면 누락은 보간하고, 팔의 32단면은 distal→proximal로 추적해 근위 합류를 배제합니다. 팔은 중심 offset과 10mm 윤곽 여유를 별도로 적용하고 어깨를 12cm로 연결합니다. 상의 접촉 보정은 signed clearance 9mm 미만 → native OUTSIDE_SURFACE offset 10mm이며 몸통 프로파일 20mm와 하의 <16mm → 20mm 정책은 유지합니다. 2,500면 초과 의류 사본은 UV·재질 데이터 레이어를 보존한 native Decimate ratio 0.2로 정리하며 양방향 정점 표본 오차 6mm 검사를 통과해야 채택합니다. 원본 SAM 신체·템플릿 파일은 유지합니다.
- src/geometry/cloth_fit.py: SAM 크기 조정·메시 정리 후 형태를 spring rest로 설정합니다. 중력 없는 최대 36프레임(quality 8, 인장/압축/전단 강성 500) 충돌 안정화와 새 rest 대비 최종 검사를 수행하며 안정된 경우 12프레임부터 조기 종료합니다.
- ../tests/test_garment_body_template.py: 원형·기준점·품질 보고서 보존과 DB 목표가 없는 SAM 결과 메타데이터 검사. Blender가 없는 환경에서는 기하 입출력을 격리합니다.
- ../tests/test_body_sections.py: 임의 평면의 팔·손 윤곽 분리, 몸통·팔 선택, 과대 윤곽 거절과 입력 검증을 Blender 없이 검사합니다. NumPy가 필요합니다.
- ../tests/test_arm_profiles.py: 중심 offset·면적 중심의 표본 밀도 불변성·좌우 대칭·다각형 offset·방사 표본과 주기 보간의 0/2π 경계를 검사합니다. NumPy가 필요합니다.

## SQL 연결 준비 오류 모듈

- src/database/connection.py: 연결 단계에 한정해 지정된 일시 오류를 10초→2초 대기→45초 로그인으로 한 번 재시도합니다. 쿼리·commit을 재생하지 않으며 재연결 실패는 일반 DatabaseUnavailable로 전달합니다.
- src/api/garments.py::database_unavailable: DatabaseUnavailable/OperationalError를 비밀 없는 HTTP 503 + Retry-After 5초로 반환합니다. 포함된 fit 라우터에도 적용됩니다.
- ../tests/test_database_retry.py: 실제 DB 없이 pyodbc 연결·트랜잭션 실행 횟수와 오류 응답을 검사합니다.
