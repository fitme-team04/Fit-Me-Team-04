> Current policy: normalized measures only for tops; brand tables only for bottom selection/fit; pants geometry is static. See garment-generation-policy.md. The inspection history below predates this policy.

# 실제 fitme DB 확인 및 브랜드 테이블 연결

2026-11-16, 기존 Azure CLI 계정의 Entra 인증과 .NET SQL Client로 `fitme-sql-dev/fitme`에 직접 접속했습니다. SQL 비밀번호·스토리지 키 조회나 ODBC 설치 없이 SELECT만 실행했으며 DB 데이터·스키마·방화벽·권한은 변경하지 않았습니다. 개인 신체·계정 데이터는 읽지 않고 상품 치수 및 스키마 메타데이터만 확인했습니다.

## 실제 저장 구조

- 기존 정규화 상품: 22개, 상품·사이즈 조인 189행. `garment.measures`의 옷 실측은 상의 중심이며 하의 필수 네 코드가 없습니다. `basis='body'`의 허리·엉덩이둘레는 권장 신체치수이므로 옷 실측으로 사용할 수 없습니다.
- 아래 시연 6개 상품은 정규화 상품 목록에는 없고 세 브랜드별 사이즈 테이블에만 있습니다.

| 테이블 | 상품 코드 | 종류 | 실제 사이즈 수 |
| --- | --- | --- | ---: |
| `garment.size_musinsa_standard` | `1144989` | 상의 | 6 |
| 같은 테이블 | `1149329` | 하의 | 13 |
| `garment.size_topten` | `MSG4TS1401BK` | 상의 | 7 |
| 같은 테이블 | `MSG3PP1401BK` | 하의 | 7 |
| `garment.size_ziozia` | `ABG4ET1104KH` | 상의 | 4 |
| 같은 테이블 | `ABG4PP1110DNV` | 하의 | 5 |

총 42행이며 이 중 하의 25행, 상의 17행입니다. 세 테이블의 `category`는 `tops`/`bottoms`, 상품 번호는 `product_id`, 사이즈는 `size_label`입니다. 숫자 상품·사이즈 ID는 없습니다.

## 코드 반영

`database/brand_catalog.py`가 허용 목록의 세 테이블만 읽습니다. 상품 번호는 SQL 매개변수로 전달합니다.

| 실제 컬럼 | 3D 입력 변환 |
| --- | --- |
| `waist_girth_cm` | `waist_width` = 값 ÷ 2 |
| `hip_girth_cm` | `hip_width` = 값 ÷ 2 |
| `thigh_girth_cm` | `thigh_width` = 값 ÷ 2 |
| `inseam_cm` | `inseam` = 값 그대로 |
| `chest_girth_cm` | `chest_width` = 값 ÷ 2 |
| `shoulder_width_cm` | `garment_shoulder_width` = 값 그대로 |
| `arm_length_cm` | `sleeve_length` = 값 그대로. 해당 세 브랜드의 notes에 어깨 기준 소매임이 명시됨 |

무신사·지오지아의 `inseam_cm`은 notes에 총장−밑위 계산값이라고 적혀 있습니다. 원본 안쪽 기장 실측이라고 바꾸어 설명하지 않고 근거를 결과 메타데이터에 보존합니다. TOPTEN은 원본 인심 값입니다.

### 조회·생성 API

- `GET /api/garments/brand-catalog`: 신규 6개 상품과 실제 사이즈 개수.
- `GET /api/garments/by-item/{item_code}/sizes`: 기존 정규화 사이즈가 없으면 브랜드 테이블의 정확한 사이즈명을 반환. `size_id`와 `garment_id`는 `null`이며 가짜 ID를 만들지 않습니다.
- `POST /api/garments`: 기존 숫자 ID 방식은 유지하고, 아래 상품 번호+사이즈명 방식도 지원합니다. 정규화 조회 결과가 없을 때 브랜드 테이블로 연결합니다.

```json
{"item_code":"MSG3PP1401BK","size_label":"M(31)"}
```

기존과 같은 `X-FitMe-Subject` 헤더가 필요합니다. 지오지아 `XXL(90)`과 `XXL(94)`는 별개 사이즈이므로 `XXL`로 축약하지 않습니다. 원본 치수표에 없는 판매 옵션은 생성하지 않습니다.

### 핏 판정

`POST /fit`도 정규화 상품이 없으면 브랜드 테이블을 읽습니다. 둘레를 단면으로 정규화한 뒤 기존 `sizes_from_db_rows`가 한 번만 다시 둘레로 바꾸게 해 ×2 중복을 방지했습니다. 6개 상품 모두 총장 없이 핏 판정이 가능합니다. 원본 판정 결과 구조는 유지합니다.

## DB 전체에서 확인한 미해결 데이터

DB 전체 사용자 테이블·뷰의 컬럼, 전체 측정 별칭 134개, 측정 정의, 설명 메타데이터 및 기존 상품 목록을 확인했습니다.

1. **세 브랜드 상의의 총장은 없음.** 세 테이블에 컬럼이 없고 기존 정규화 상품에 해당 상품 코드도 없습니다. 다른 상품의 총장이나 신체 torso_length를 복사하지 않습니다. 따라서 상의 3D 요청은 `body_length` 누락으로 422이며, 핏 판정은 가능합니다.
2. **유니클로 소매는 뒷목 기준.** `ref.measure_aliases`의 `source_name='uniqlo_site'`, `alias_name='sleeve-length-cb'`를 확인했습니다. 앞선 TOP 100 조회로 별칭이 없는 것처럼 보인 문제를 조회 상한 확대 후 정정했습니다. 현재 상의 원형 변형은 어깨 기준 전용이므로 유니클로를 쓰려면 별도의 측정 기준 환산도 필요합니다.
3. **웹의 기존 선택 계약은 숫자 ID 중심.** 기존 카탈로그 응답은 유지했습니다. 신규 상품은 새 브랜드 카탈로그와 상품 코드+정확한 사이즈명 경로를 웹에서 사용해야 합니다. 웹 UI·VM 설정·배포는 이번 DB 연결 작업에서 변경하지 않았습니다.

## 검증

- 실제 DB 상품 치수 42행 스냅샷으로 세 하의의 API 생성 연결, 6개 상품 핏 판정, 정확한 사이즈명·누락 총장 처리를 검사했습니다.
- 무신사 `1149329/32`, TOPTEN `MSG3PP1401BK/M(31)`, 지오지아 `ABG4PP1110DNV/XL(86)`의 실제 DB 값으로 Blender worker GLB 생성을 확인했습니다. 신체 교차 보정은 하지 않습니다.
- 브랜드 연결 7개, 기존 `/fit` 5개, 하의 네 입력 4개의 총 16개 API·계약 테스트가 통과했습니다.
- 재점검 도구: `scripts/inspect_sql_catalog.ps1`. 토큰을 출력·저장하지 않고 읽기 전용 보고서만 로컬 캐시에 저장합니다.


UNIQLO live audit: garment.measures contains garment-basis dimensions for 13 UNIQLO products, 116 sizes, 457 rows (body_length=116, chest_width=116, garment_shoulder_width=109, sleeve_length=116). The missing body_length issue concerns the 3 separate brand-table demo tops, not these UNIQLO products. Picture-based F-to-G conversion was canceled; original DB values and center-back aliases are preserved.
