# fetch — 공개 데이터·코드를 받는 파이썬 패키지

## 들어 있는 것
| 그룹 | 내용 | 모듈 |
|---|---|---|
| [garment/](<garment/README.md>) | 옷 치수 (사이즈표·실측) | kobo_garment_measurements, oh_my_measure, uniqlo_garment_json, uniqlo_site, zozotown_page |
| [fit/](<fit/README.md>) | 신체 ↔ 구매 사이즈 짝 (리뷰·후기) | uniqlo_size_predictor, uniqlo_size_recommendation, musinsa_ml_project |
| [body/](<body/README.md>) | 신체 치수 (인체측정 조사) | ansur2, bodym, nhanes |
| [model/](<model/README.md>) | 코드·모델 (치수 계산, 예측, 3D 몸) | clad_body, uniqlo_body_size_pred, anny |
| `_common.py` | 공통 함수: `SOURCES_DIR`(= `opensource/sources`), `get`·`api_get`·`download`, GitHub 커밋 zip 받기 `github_zip`, 표준 라이브러리 xlsx 읽기 `read_xlsx` | |
| `__init__.py` | 전체 목록 `SOURCES` (쓸 때만 import) | |

모듈 규격: `NAME`(받는 폴더 이름 = 모듈 파일 이름 = DB `source_name` 값, 예 `kobo_garment_measurements`), `fetch(dest) -> dict`(받기, 폴더에 파일이 있으면 `[건너뜀]`), `sample(dest, n=3)`(받은 파일에서 실제 레코드 출력).

## 사용법
하나만 받고 샘플 보기 (`opensource` 폴더에서):
```bash
python -m fetch.<그룹>.<모듈>          # 예: python -m fetch.body.ansur2
```
전부 받기 (`opensource` 폴더에서 `python` 실행 후):
```python
from fetch import SOURCES
from fetch._common import SOURCES_DIR
for src in SOURCES:
    print(src.fetch(SOURCES_DIR / src.NAME))
```
받은 파일은 `opensource/sources/<NAME>/` 에 쌓인다. Teams 에 올리지 않는다 — 각자 받는다.

받은 데이터 목록·용량 보기: `python -m fetch.manifest` (sources/sources.lock.json 갱신, 네트워크 안 씀)

## 주의
- 큰 파일: nhanes 는 기본으로 약 283MB. 선택 옵션 `bodym.fetch(dest, with_images=True)` 약 90MB.
- 이미 받은 소스는 `[건너뜀]`. 다시 받으려면 `sources/<NAME>` 폴더를 휴지통으로 옮긴 뒤 실행한다.
- 라이선스가 없거나 사이트 약관만 있는 소스는 PoC 전용(재배포·상업 이용 금지). 그룹별 README 의 표를 확인한다.
