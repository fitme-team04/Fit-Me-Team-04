# garment — 상품 목록, 사이즈별 치수

## 들어 있는 것
| 파일 | 하는 일 | 언제 쓰나 (예) |
|---|---|---|
| `01_garment_list.sql` | 브랜드·카테고리별 상품 목록 + 사이즈 개수 | 유니클로 상품이 몇 개 적재됐는지 볼 때 |
| `02_size_measures.sql` | 한 상품의 사이즈별 치수: 옷 실측(`garment`) / 권장 체형(`body`, low~high) | 상품 상세의 사이즈표를 만들 때 |

## 사용법
1. 01: `@brand` (예: `'UNIQLO'`), `@category` 를 정해 실행. `NULL` 이면 전체.
2. 01 결과의 `garment_id` 를 02 의 `@garment_id` 에 넣어 실행.

## 주의
- 옷 실측은 단면(펼친 너비) 값이다. 둘레와 비교하려면 `ref.measure_maps` 의 factor(×2)를 쓴다 → `recommend/`.
