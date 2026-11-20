# model — 코드·모델 소스 (치수 계산, 예측 모델, 3D 몸)

## 들어 있는 것
| 모듈 | 출처 | 무엇을 받는지 | 라이선스/주의 |
|---|---|---|---|
| `clad_body` | GitHub datar-psa/clad-body | Anny/MHR 3D 몸 메시에서 ISO 8559-1 치수 25개를 계산하는 코드 (데이터 없음) | Apache-2.0 |
| `uniqlo_body_size_pred` | GitHub yusuke0127/body-size-pred + 유니클로 공식 치수표 이미지 2장 | 성별·나이·키·체중 → 가슴·허리·엉덩이(mm) 예측 모델(`model.pkl`) → XS~4XL 추천. 학습 데이터는 없음 | 라이선스 없음, PoC 전용. 치수표 이미지는 유니클로 저작물 |
| `anny` | GitHub naver/anny | NAVER 3D 인체 파라메트릭 모델 코드. 입력은 성별·나이·근육·체중·키 등 0~1 값 | Apache-2.0. 실행 중 받는 일부 자산은 비상업 전용 |

## 사용법
```bash
cd opensource
python -m fetch.model.clad_body
```
`fetch`/`sample` 은 코드를 받고 내용만 읽는다 (torch 불필요). 실제로 모델을 돌리려면 `pip install -r requirements.txt` (torch·anny·clad-body 등).

## 주의
- 파이프라인에서: 이후 단계. 추정한 부위 치수와 자세(`body.poses`·`body.measures`)로 3D 몸 모델을 만들 때 쓴다.
- 키 불필요.
