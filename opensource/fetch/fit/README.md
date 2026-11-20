# fit — 신체 ↔ 구매 사이즈 짝 소스 (리뷰·후기)

## 들어 있는 것
| 모듈 | 출처 | 무엇을 받는지 | 라이선스/주의 |
|---|---|---|---|
| `uniqlo_size_predictor` | GitHub alviskwok/uniqlo_size_predictor | 유니클로 일본 리뷰: 성별·연령대·키·체중·발 크기 → 구매 사이즈·별점, 상품 100개 (`df.csv`, `item list.xlsx`) | 라이선스 없음, PoC 전용 |
| `uniqlo_size_recommendation` | GitHub jackfai1993/Uniqlo_Size_Recommandation | 위와 같은 팀 저장소. `df.csv`, `df_20220323ver.csv`(Dept 열 포함), `item list.xlsx` | 라이선스 없음, PoC 전용 |
| `musinsa_ml_project` | GitHub parkmy0420/ML_project | 무신사 상의 실측 사이즈표(총장·어깨·가슴단면·소매, cm) + 후기(키·몸무게·고른 사이즈), 2023-06 크롤링 | 라이선스 없음, PoC 전용. 무신사 공식 아님(2차 자료) |

## 사용법
```bash
cd opensource
python -m fetch.fit.uniqlo_size_predictor
```

## 주의
- 파이프라인에서: 신체 정보는 `body.profiles`, 고른 사이즈는 `garment.sizes` 로 들어가 "이 몸이면 이 사이즈" 정답 쌍(학습·검증용)이 된다.
- 키 불필요. 모두 상업 이용 불가로 취급한다.
