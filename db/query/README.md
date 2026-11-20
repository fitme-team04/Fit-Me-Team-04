# query — 목적별 사용 SQL (초기화에는 포함 안 됨)

## 들어 있는 것
| 폴더 | 하는 일 |
|---|---|
| `user/` | 회원 등록·수정, 신체 정보·부위 치수 입력 |
| `body/` | 한 사람의 신체 치수 조회, 부위별(팔·다리·몸통·목) 조회 |
| `garment/` | 브랜드·상품 목록, 상품의 사이즈별 치수 (옷 실측 / 권장 체형) |
| `recommend/` | 사이즈 추천: 내 치수 ↔ 옷 치수, 여유분 = 옷 × factor − 몸 |
| `train/` | AI 학습 데이터: 1명 = 1행으로 펼치기, 출처별 항목 채움 현황 |
| `check/` | 적재 점검: 테이블 행 수, 별칭 없는 측정명, 값 없는 사이즈 |

## 사용법
1. 쓸 파일을 열고 맨 위 `SET @... = ...;` 값을 바꾼다 (예: `@user_id`, `@garment_id`).
2. 실행 (db 폴더에서): `docker exec -i poc-mysql mysql -uroot -ppoc-root --default-character-set=utf8mb4 -t < query/recommend/01_size_fit.sql`
3. 또는 DB 도구(Workbench·DBeaver 등)에 파일 내용을 붙여 넣고 전체 실행.

## 주의
- `user/` 파일은 데이터를 넣거나 고친다. 나머지 폴더는 조회만 한다.
- 컨테이너가 꺼져 있으면 먼저 `bash ../up.sh` (db 폴더 README 참고).
