# body — 신체 치수 조회

## 들어 있는 것
| 파일 | 하는 일 | 언제 쓰나 (예) |
|---|---|---|
| `01_my_measures.sql` | 한 사용자의 최근 신체 정보 + 치수 전체 (부위·종류 포함) | 화면에 "내 치수"를 보여 줄 때 |
| `02_by_body_part.sql` | 부위별 치수 (뷰 `arm/leg/torso/neck_measures`) | 상의는 팔·몸통, 하의는 다리만 볼 때 |

## 사용법
1. 01: `@user_id` 를 바꿔 실행 (가장 최근 `profiles` 행 기준).
2. 02: `@profile_id` 를 바꾸고 필요한 부위 SELECT 만 실행해도 된다.

## 주의
- 부위(`body_part`)·종류(`measure_type`)는 `ref.measure_definitions` 에서 온다. 새 항목은 `sql/50_seed_measure_definitions.sql` 에 추가.
