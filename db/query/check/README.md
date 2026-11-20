# check — 적재 점검

## 들어 있는 것
| 파일 | 하는 일 | 언제 쓰나 (예) |
|---|---|---|
| `01_table_rows.sql` | 모든 테이블의 정확한 행 수 | 데이터 적재 전후로 몇 행 들어갔는지 볼 때 |
| `02_unknown_alias.sql` | 수집 파일 열 이름 중 `ref.measure_aliases` 에 없는 것 | 새 데이터셋을 적재하기 전에 |
| `03_empty_sizes.sql` | 치수가 하나도 없는 사이즈, 값이 전부 빈 치수 행 | 크롤링 결과가 제대로 들어갔는지 볼 때 |

## 사용법
1. 01, 03 은 그대로 실행.
2. 02 는 `@source_name` 과 `@alias_names` (열 이름 JSON 배열, 예: `'["stature", "footlength"]'`)를 바꿔 실행.
3. 02 결과에 나온 이름은 `sql/51_seed_measure_aliases.sql` 에 추가하고 `up.sh` 를 다시 실행.

## 주의
- 모두 조회만 한다. 데이터를 고치지 않는다.
