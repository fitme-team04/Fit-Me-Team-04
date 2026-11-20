# garment — 옷 치수 (사이즈표·실측) 소스

## 들어 있는 것
| 모듈 | 출처 | 무엇을 받는지 | 라이선스/주의 |
|---|---|---|---|
| `kobo_garment_measurements` | GitHub kobo-labs-open-source/garment-measurements | 측정 지점(POM) 41개 정의, 사이즈표 5종(US/EU/UK/AU), 그레이드 규칙. cm | MIT. `*-width` 는 반폭 → 둘레는 ×2 |
| `oh_my_measure` | Hugging Face fedorovvvv/oh-my-measure-brand-size-charts | 132개 브랜드 사이즈표 496개를 합친 긴 표 (가슴·허리·엉덩이 범위, cm) | "other" — 권리·라이선스 없음, PoC 전용. 값은 대부분 몸 둘레(옷 실측 아님) |
| `uniqlo_garment_json` | GitHub Prisha-3012/Curate---HackMIT | 유니클로 상품 2개(크루넥 T, 옥스퍼드 셔츠) 사이즈별 가슴·어깨 범위 | 라이선스 없음, PoC 전용. 해커톤 작성 값(공식 표 아님) |
| `uniqlo_site` | uniqlo.com (Commerce API v5, 사이즈표 이미지) | us/jp/kr 상품 검색 → 상품 실측·체형 사이즈표, `size_charts.csv`(정규화) | 사이트 약관. PoC 내부 참고용, 재배포 금지 |
| `zozotown_page` | zozo.jp 상품 페이지 (차단 시 tri-star/just-fit fixture) | アイテムサイズ 실측표 → `measurements.csv`, 접근 기록 `access_log.json` | 약관 미확인, PoC 내부용·재배포 금지. 403 이면 우회 없이 중단 |

## 사용법
```bash
cd opensource
python -m fetch.garment.kobo_garment_measurements
```

## 주의
- 파이프라인에서: 브랜드별 옷 치수 → `garment.brands / garments / sizes / measures` 에 적재해, 추정한 신체 치수와 비교하는 기준으로 쓴다.
- 키 불필요. 공식 데이터가 아닌 소스가 많으니 상용 전환 시 교체 대상이다.
