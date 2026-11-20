# FitMe 3D 서비스

dev에서 이어진 `feature/3d-deploy`의 3D 서비스 코드입니다. 원래 `fitme_avatar/`와 `fitme_garment/`를 기존 연동 폴더 아래로 이관했습니다.

| 경로 | 역할 |
|---|---|
| `avatar/` | GPU VM의 신체 생성 API, SAM 추론, ML 배포 코드 |
| `garment/` | CPU VM의 의류 생성 API와 Three.js 웹 뷰어 |
| `tests/` | 모델 다운로드·API 계약·모듈 경로의 회귀 테스트 |
| [DEPLOYMENT.md](DEPLOYMENT.md) | 인증·실행·SQL 준비 절차 |
| [db/azure/3d/](../../db/azure/3d/README.md) | 공통 DB 재사용·구형 레시피 테이블 제거 절차 |

각 서비스의 `src/`는 다음 기준으로 나눴습니다.

| 패키지 | 기능 |
|---|---|
| `api/` | HTTP 요청·응답 |
| `core/` | 입력 계약, 치수 검증, Blender 프로세스 실행 |
| `geometry/` | 메시·GLB·앵커·템플릿 변형 |
| `storage/` | 결과 Blob 저장, 원본 모델 검사 |
| `inference/` | 신체 서비스의 SAM 추론 |
| `database/` | 의류 상품·실측의 Azure SQL 조회 |
| `checks/` | 의류 서비스의 DB·GLB 생성 점검 |

소유 코드에는 첫 부분에 한국어 역할 주석을 붙였습니다. 외부 `avatar/vendor/sam-3d-body/` 및 빌드된 뷰어 번들은 원본과 라이선스를 유지합니다.
JSON 같은 주석을 지원하지 않는 설정은 유효한 형식을 유지합니다.

14개 회귀 테스트는 `python -m unittest discover -s tests -v`로 실행합니다.
API 의존성과 NumPy·PyYAML이 설치된 환경에서는 `python tests/smoke_services.py`로
실제 API import·모의 ML 응답·의류 템플릿 조회·Compose 정의를 추가 검사합니다.
GPU·Blender 프로세스와 실제 Azure 네트워크를 실행하는 통합 검사는 별도입니다.

## API 계약

- 신체: `POST /api/avatars`, 포트 8001. 사진 원본 바이트, `height-cm`·`weight-kg` 헤더와 인증 프록시의 `X-FitMe-Subject`를 받습니다.
- ML: 실제 키·몸무게와 SAM 측정값 11개(cm)를 Azure ML 실시간 엔드포인트에 보내고 `male` 아래 키 제외 치수 28개를 받습니다. 실제 입력 키를 합쳐 Blob 기본 모델을 변형합니다. [ML 계약·실행 방법](../../avatar/azureml/README.md)을 확인하세요.
- 의류: `POST /api/garments`, 포트 8002. `item_code`·`size_id`로 실측을 읽고 category·측정 별칭으로 생성 방법을 결정합니다. 기존 garment_id 입력도 호환합니다.
- 조회: `GET /api/garments`, `GET /api/garments/{garment_id}/sizes`.
- 결과: `status`, `model_id`, GLB·앵커 URL을 반환합니다. 신체는 치수 보고서 URL도 제공합니다.

프런트의 `BODY_MODEL_VM_URL`, `GARMENT_MODEL_VM_URL` 및 인증 프록시 계약은 유지합니다.
각 서비스의 `architecture/`에서 최신 호출 관계와 파일 역할을 확인할 수 있습니다.

신체 원본 네 파일은 `fitmemlstdev/avatar-models`에만 보관하고 Git에는 넣지 않습니다.
`validation/` 결과물은 제거했으며, 회귀 검사는 결과물을 저장하지 않고 `tests/`와 점검 도구로 수행합니다.
