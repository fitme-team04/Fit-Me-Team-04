# body — 신체 치수 소스 (인체측정 조사)

## 들어 있는 것
| 모듈 | 출처 | 무엇을 받는지 | 라이선스/주의 |
|---|---|---|---|
| `ansur2` | Penn State OpenLab (ANSUR II 2012 미군 조사) | 남 4,082명·여 1,986명 CSV + 측정 정의서 PDF | 명시 없음(공개 승인 자료). 치수 mm, `weightkg` 는 0.1kg 단위 → ÷10 |
| `bodym` | Amazon BodyM (공개 S3 `amazon-bodym`) | 키·체중·성별 + 14개 신체 치수(cm) CSV. `with_images=True` 면 실루엣 이미지(약 90MB) | CC BY-NC 4.0 (비상업) |
| `nhanes` | Hugging Face gracemyu/nhanes-merged (리비전 고정) | NHANES 1999~2017·2021 통합 parquet(약 283MB): 키·체중·팔/다리 길이·둘레·체지방 | CC0-1.0. 기본으로 283MB 받음 |

## 사용법
```bash
cd opensource
python -m fetch.body.ansur2
```
nhanes `sample()` 은 `pyarrow` 가 있으면 로컬 parquet 를, 없으면 CDC 원본 XPT 를 읽는다 (`pip install pyarrow==26.0.1`, 선택).

## 주의
- 파이프라인에서: `body.profiles`(`user_id` NULL = 데이터셋 행) + `body.measures`(measure_method = measured) 로 들어가, 체형 → 부위 치수 AI 추정 모델의 학습 데이터가 된다.
- 키 불필요.
