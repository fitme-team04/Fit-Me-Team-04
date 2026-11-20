# 현재 의류 생성 정책: SAM 피팅과 신체 없는 의류 생성

## SAM 신체가 있는 피팅

`body_model_id`가 있는 요청은 상품·사이즈 존재를 확인하고 category에 맞는 등록 원형을 선택합니다. `garment.measures`와 `ref.measure_aliases`는 조회하지 않으며 상품 실측의 누락·범위·중복 검증도 하지 않습니다. API는 빈 `spec`과 `geometry_mode=sam_body`를 전달합니다.

worker의 `template_binding.body_template`은 상의·하의 모두 원형 정점과 등록 anchor reference를 유지합니다. 원형 해시·바인딩 버전·메시 품질은 검사합니다. 그 뒤 실제 SAM 자산을 읽는 Cloth 피팅 단계에서 신체 기준 크기를 적용합니다. 결과에는 `fitting_mode=sam_body_cloth_collision`을 사용하고 `cloth_simulation.body_sizing`에 신체 기준 크기 조정 내역을 보존합니다. `fitme_garment_measurements`는 비워 상품 DB 목표값을 달성한 것처럼 표시하지 않습니다.

이 경로의 3D 크기는 선택 상품의 실측 크기가 아닙니다. `/fit`의 상품 실측 기반 판정은 별도로 유지합니다. 다음 상의·하의 정책은 `body_model_id`가 없는 의류 단독 생성에 적용합니다.

## 신체 없는 상의 생성

상품·사이즈는 `garment.garments`와 `garment.sizes`에서 선택하고, 옷 실측은 **`garment.measures`의 `basis='garment'`만** 사용합니다. 브랜드별 `size_*` 상의로 우회하지 않습니다. 소매 기준은 기존 `ref.measure_aliases`를 조회하며 그림 기반 추정 환산은 취소된 상태입니다.

상의 총장·어깨너비·가슴너비·소매길이는 기존 계약대로 필요합니다. 누락된 값은 브랜드 테이블이나 다른 상품 값으로 채우지 않습니다. 현재 상의 원형의 소매 기준·변형 범위 제한도 유지합니다.

상의 `/fit` 판정 역시 정규화 실측만 사용합니다. 브랜드 테이블에만 있는 상의는 3D 생성과 핏 판정에 사용하지 않습니다.

## 신체 없는 하의 생성

선택한 상품·사이즈의 존재는 계속 확인하지만 **상품 실측으로 3D 메시를 변형하지 않습니다.** `garment_worker`가 하의 치수 검증을 건너뛰고 빈 `spec`으로 원본을 로딩합니다. `template_binding.static_template`은 정점을 수정하지 않고 등록 당시 허리·샅·양 밑단 기준점을 고정해 반환합니다.

하의 실측이 없거나 다른 값을 전달해도 같은 기본 메시를 내보냅니다. 원본 파일·등록 정보·자세 기준은 필요합니다. 입력 형식이나 모델 파일 오류까지 무조건 성공 처리하는 것은 아닙니다. 신체 교차 보정·출력 차단은 없습니다.

`black_midrise_straight_v1`의 정책은 `static`, revision은 `1.2`, 조절 필드는 없습니다. `pants/garment-spec.json`은 `{}`입니다. GLB의 `spec`과 `fitme_garment_measurements`도 비우고 `template_geometry.deformation_applied=false`, `geometry_mode=static`으로 명시해 실제 상품 실측을 반영한 모델로 오해하지 않게 합니다.

## 하의 선택과 핏 판정

브랜드별 테이블은 **하의 선택과 실제 핏 판정에만** 사용합니다. `/api/garments/brand-catalog`는 하의 3개 상품·25개 사이즈만 노출합니다. 상품 코드+정확한 사이즈명으로 선택하는 방식과 기존 숫자 ID 방식은 유지합니다.

`/fit`은 하의의 실제 허리·엉덩이둘레로 판정하며 고정 3D 모델의 폭으로 판정하지 않습니다. 따라서 다른 사이즈를 골랐을 때 판정 결과는 바뀔 수 있지만 하의 3D 형상은 같습니다.

## 검증·배포

- 상의는 `measures`만 사용하고 브랜드 조회를 하지 않는 API 검사.
- 하의 실측 누락·불필요 치수를 무시하고 원형 출력 요청을 만드는 API 검사.
- 브랜드 상의의 생성·핏 우회가 거절되고 하의 브랜드 선택·판정은 유지되는 검사.
- 실제 Blender에서 무치수·작은 치수·큰 치수 세 요청의 정점·면이 원본과 정확히 같고, 네 기준점도 동일하며 실제 게시용 앵커 추출을 통과함을 확인했습니다.

통합 폴더의 코드·registry·조절 JSON도 갱신했습니다. VM 배포와 Blob 업로드는 수행하지 않았습니다. 이전 네·일곱 치수 변형 검사 결과는 과거 정책 기록이며 현재 정책 검사는 `pants/static-validation/`에 있습니다.


Current model startup: native center-back shirt body_center_back_v19 and static pants are loaded once from garment-models through the pinned manifest and resident Blender. Earlier shoulder-only and Docker local-template notes are superseded. See docs/blob-resident-models.md. Manual Blob upload is pending; VM deployment was not performed.
