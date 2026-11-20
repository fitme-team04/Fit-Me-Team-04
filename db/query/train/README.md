# train — AI 학습 데이터 추출

## 들어 있는 것
| 파일 | 하는 일 | 언제 쓰나 (예) |
|---|---|---|
| `01_wide_by_profile.sql` | 1명 = 1행 (키·체중 + 치수 12개 열), 실측값만 | 학습용 CSV 를 뽑을 때 |
| `02_measure_coverage.sql` | 출처 × 항목별 인원 수·평균·최소·최대 | 어떤 항목을 학습 열로 쓸 수 있는지 고를 때 |

## 사용법
1. 02 로 출처별로 채워진 항목을 먼저 본다.
2. 01 의 `@source_name` 을 정하고 (`'ansur2'`, `'bodym'`, `NULL` = 전체) 필요한 열의 `MAX(CASE ...)` 줄을 추가·삭제.
3. CSV 로 받기: `docker exec -i poc-mysql mysql -uroot -ppoc-root -B < query/train/01_wide_by_profile.sql > train.tsv` (탭 구분)

## 주의
- AI 추정값(`measure_method = 'estimated'`)은 학습에서 뺀다 (추정값으로 다시 학습하지 않기 위해).
- 출처마다 정의가 조금 다른 항목이 있다 (`sql/51_seed_measure_aliases.sql` 주석 참고).
