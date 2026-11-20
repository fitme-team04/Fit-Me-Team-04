# 아키텍처 — DB 구조(ERD)와 데이터 흐름 그림

## 들어 있는 것
| 파일 | 내용 |
|---|---|
| `ERD.png` | MySQL 테이블 구조. 스키마 3개: `body`(사용자·신체), `ref`(치수 항목 정의), `garment`(브랜드·옷·사이즈) |
| `ERD.drawio` | ERD 원본 (편집용) |
| `데이터흐름.png` | ① 데이터 소스(앱 입력, fetch 그룹) → ② DB → ③ 처리(AI 추정 모델, 비교·매칭) → ④ 결과(3D 몸 모델, 사이즈 추천) |
| `데이터흐름.drawio` | 데이터 흐름 원본 (편집용) |
| `Azure구성.png` / `.drawio` | Azure PoC 배포 구성 (VM 의 MySQL + 예약 실행 Container Apps Job). 흐름 ①~⑦ 은 그림 아래 범례 |

## ERD 읽는 법
- 표기: `PK` 기본키, `FK` 외래키, `UQ` 유니크, `IX` 인덱스, `CK` CHECK 제약(허용값·형식, 예: `body.profiles.body_type`), 밑줄 = 기본키 컬럼. 선 끝 까마귀발(여러 개) 쪽이 FK, 두 줄 쪽이 PK (N:1).
- 치수 값은 긴 형식(long format): 1행 = 1항목. 예) `body.measures` 는 (사람 `profile_id`, 항목 `measure_code`) 하나가 한 행, `garment.measures` 는 (사이즈, 항목, 기준 `basis`) 하나가 한 행.
- 항목 코드는 모두 `ref.measure_definitions.measure_code` 를 가리킨다. 소스마다 다른 이름은 `ref.measure_aliases`, 신체 항목 ↔ 옷 항목 대응은 `ref.measure_maps`.
- 브랜드는 열이 아니라 행이다: `garment.brands` 에 한 줄씩 추가한다.
- 신체 부위는 `ref.measure_definitions.body_part` 열로 구분하고, 부위별로 보려면 뷰 `body.arm_measures / leg_measures / torso_measures / neck_measures` 를 쓴다.
- `garment.measures.basis` = `garment` 이면 옷 실측(`value_cm`), `body` 이면 권장 신체 범위(`low_cm`~`high_cm`).

## 사용법 (그림 고치기)
1. draw.io(데스크톱 또는 app.diagrams.net)로 `.drawio` 파일을 연다.
2. 고친 뒤 저장하고, 파일 > 내보내기 > PNG 로 같은 이름(`ERD.png`, `데이터흐름.png`)에 덮어쓴다.

## 주의
- 정본은 `../db/sql/*.sql` 이다. 테이블을 바꾸면 SQL 을 먼저 고치고 그림을 맞춘다.
- 인덱스 상세는 `../db/테이블_정의서/` 스키마별 파일의 인덱스 시트.
