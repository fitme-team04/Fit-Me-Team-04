# user — 회원 등록·수정, 신체 정보 입력

## 들어 있는 것
| 파일 | 하는 일 | 언제 쓰나 (예) |
|---|---|---|
| `01_upsert_user.sql` | 회원 등록, 같은 email 이면 수정 | 새 팀원·테스트 사용자를 만들 때 |
| `02_insert_profile.sql` | 키·체중·근육량·체지방률 입력 (새 행 = 이력), 체형 `body_type` 은 키·체중 BMI 로 계산해 같이 저장 | 사용자가 신체 정보를 처음/다시 입력할 때 |
| `03_upsert_measure.sql` | 가슴둘레·팔길이 등 부위 치수 입력·수정 | 줄자 실측값이나 AI 추정값을 저장할 때 |

## 사용법
1. 01 실행 → 결과의 `user_id` 를 02 의 `@user_id` 에 넣는다.
2. 02 실행 → 결과의 `new_profile_id` 를 03 의 `@profile_id` 에 넣는다.
3. 03 의 `VALUES` 줄을 측정값으로 바꿔 실행.

## 주의
- `measure_code` 는 `ref.measure_definitions` 에 있는 코드만 된다 (`SELECT measure_code, korean_name FROM ref.measure_definitions;`).
- AI 추정값은 `measure_method = 'estimated'`, `model_version` 에 모델 이름을 넣는다.
