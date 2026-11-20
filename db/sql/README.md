# sql — 초기화 세트 (테이블·뷰·시드)

## 들어 있는 것
| 파일 | 하는 일 |
|---|---|
| `00_schemas.sql` | 스키마 `body` / `garment` / `ref` 생성 (utf8mb4) |
| `10_ref_*` ~ `12_ref_*` | 치수 항목 정의 `measure_definitions`, 출처별 이름 변환 `measure_aliases`, 신체↔옷 대응 `measure_maps` |
| `20_body_*` ~ `23_body_*` | `users`, `profiles`, `measures`, `poses` |
| `24_body_profiles_body_type.sql` | `profiles.body_type`(체형, 대한비만학회 BMI 단계) 컬럼 + CHECK 추가 — 없을 때만 (`information_schema` 확인 후 PREPARE) |
| `30_garment_*` ~ `33_garment_*` | `brands`, `garments`, `sizes`, `measures` |
| `40_view_body_part.sql` | 뷰 `body.measure_details` + 부위별 `arm/leg/torso/neck_measures` |
| `50_seed_*` ~ `53_seed_*` | 시드(초안): 항목 37개, 별칭 64개, 대응 8개, 브랜드 4개 |

## 사용법
- 파일 이름 순서대로 실행된다. 번호: 00 스키마, 10 ref, 20 body, 30 garment, 40 뷰, 50 시드.
- `up.sh` 가 자동 적용. 직접 할 때: `for f in sql/*.sql; do mysql -h127.0.0.1 -uroot -p"$PW" < "$f" || break; done`
- MySQL 이미지 `/docker-entrypoint-initdb.d` 에 이 폴더를 그대로 넣어도 된다 (`*.sql` 이름순 실행).
- 새 테이블·시드: 알맞은 번호대에 새 파일 추가 (예: `34_garment_xxx.sql`, `54_seed_xxx.sql`). 이름은 `../테이블_정의서/공통.xlsx` 명명 규칙 시트를 따른다.

## 주의
- 모든 파일은 여러 번 실행해도 안전해야 한다: `CREATE TABLE IF NOT EXISTS`, 인덱스는 CREATE TABLE 안에, `CREATE OR REPLACE VIEW`, 시드는 `INSERT ... ON DUPLICATE KEY UPDATE`, `ALTER TABLE` 은 `information_schema` 로 있는지 보고 없을 때만 (`24_` 참고, MySQL 8.0 에는 `ADD COLUMN IF NOT EXISTS` 가 없음).
- 이름은 `body.users` 처럼 스키마까지 쓴다. `USE`, `DELIMITER`, 계정·비밀번호는 넣지 않는다.
- 이미 만든 테이블은 `IF NOT EXISTS` 때문에 파일을 고쳐도 바뀌지 않는다 — 컬럼 변경은 새 번호 파일에 `ALTER TABLE` 로.
