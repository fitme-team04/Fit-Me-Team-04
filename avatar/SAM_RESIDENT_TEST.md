# SAM 상주 및 범위 보정 배포 확인

코드를 신체 VM에 반영하고 이미지를 다시 빌드해야 합니다. 기존 단일 uvicorn 워커를 유지합니다.
상주 모드는 시작 시 SAM·검출기·MoGe와 기준 모델을 로드하고, 준비되기 전에는 API 시작이 완료되지 않습니다.

`.env`의 `SAM_RUNTIME_MODE=resident`가 기본값입니다. `oneshot`으로 바꾸고 컨테이너를
다시 생성하면 이전 요청별 모델 로드 방식으로 돌아갑니다. Azure ML 연결 설정은 그대로 사용합니다.
키·토큰·환경 파일 내용은 로그나 테스트 보고서에 출력하지 않습니다.

## 실제 VM 검증

1. 배포 후 컨테이너 로그에서 `Resident SAM model loaded; ready for reuse`와 API 준비를 확인합니다.
2. 사용 허가된 동일 사진으로 키 180cm, 몸무게 55·75·88kg을 순차 요청합니다.
3. 각 요청이 ready인지 확인하고 GLB·앵커·measurements.json 다운로드를 확인합니다.
4. 샅앞뒤길이 보정 시 target(ML 원본), applied_target(적용 목표), measured(메시 실측), abs_error를 비교합니다.
5. 재기동 없이 두 번째·세 번째 요청을 보내 모델 로드 로그가 반복되지 않는지 확인합니다.
6. 기존 oneshot과 resident를 같은 VM·사진·ML 엔드포인트로 비교합니다. API 시작 시간과
   시작 후 요청 시간을 분리해 기록합니다. 19초는 예상치이며 검증 전 실측 결과로 발표하지 않습니다.
7. 로그에서 422·503 detail과 FITME_ADJUSTMENT 내역을 확인합니다.

상주 프로세스가 중단되면 현재 요청은 503으로 끝나며 다음 요청에서 모델을 다시 로드합니다.
모델 전체 불일치·사진 오류·ML 통신 실패는 치수 보정으로 숨기지 않습니다.

## 로컬 검증 범위

`tests/blender_deform_limits.py`는 실제 기본 blend에서 rise 양방향 범위 초과, 너비·둘레 충돌,
높이 겹침을 검증합니다. `tests/test_sam_resident.py / tests/test_error_logging.py`는 경량 자식 프로세스로
재사용·시작/종료·시간 초과·재시작과 로그를 검증합니다. 실제 GPU 속도 및 개인 사진 검증을 대체하지 않습니다.
