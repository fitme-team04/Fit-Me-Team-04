# 웹 FastAPI와 3D 서비스 연결

웹 FastAPI는 포트 8766에서 요청을 받고 Redis의 pair 워커가 신체 생성 후 의류 FastAPI를 순차 호출합니다.

신체 API는 사진에서 SAM이 복원한 메시를 입력 키에 맞춰 동일 배율로 보정해 GLB로 저장합니다.
기본 blend는 측정 위치와 앵커 가이드에만 사용하며 ML 예측으로 최종 신체를 변형하지 않습니다.
웹 표시와 의류 계산은 같은 SAM GLB를 원본으로 사용합니다. 계산에는 선택·단순화한 파생 메시를 쓰고 최종 관통은 원본 전체로 검사합니다.

pair 워커는 검증된 신체 모델 해시를 `body_model_id`로 의류 API에 전달합니다.
의류 API는 선택 상품·사이즈의 존재와 category별 템플릿을 확인합니다. 신체가 있는 요청에서는 상품 DB 치수와 소매 별칭을 조회·검증하지 않고 원형을 읽은 뒤 실제 SAM 신체 기준으로 옷 크기를 맞춥니다.
의류 VM은 같은 계정의 BODY_STORAGE_CONTAINER(기본 body-glb)에서 요청 소유자의 신체 GLB만 읽고 해시를 검증합니다.
해당 VM 관리 ID에는 이 컨테이너의 Storage Blob Data Reader 권한이 필요합니다.
Blender는 신체와 옷의 앵커를 정렬하고 SAM 기준으로 옷 크기를 맞춥니다. 2,500면을 넘는 의류 사본은 UV·재질 데이터 레이어를 보존하는 native Decimate ratio 0.2로 미세 삼각형을 정리하며, 정리 전후 양방향 정점→표면 표본 오차가 6mm를 넘으면 실패로 저장합니다. 원본 템플릿 파일과 표시용 SAM 신체는 바꾸지 않습니다.
현재 SAM 경로는 중력 없는 신체 Collision + 옷 Cloth로 최대 36프레임 안정화합니다. quality는 8, 인장·압축·전단 강성은 각각 500이며 12프레임부터 연속 안정 조건을 충족하면 조기 종료합니다. Cloth 기준 형태는 크기 조정·메시 정리·신체 여유 보정 후의 sam_sized_template입니다. 정리 내역은 cloth_simulation.body_sizing.cloth_conditioning에서 확인합니다.
현재 상의 경로는 SAM 몸통의 높이별 중심·반지름과 실제 어깨→손목 축의 팔 표면으로 원형 크기를 맞춥니다.
상의 크기 조정에는 fit_neck_L/R·fit_shoulder_L/R·fit_wrist_L/R이 필요하며 필수 기준점 오류는 sam_sizing_failed로 저장합니다.
sam_sizing_start/complete와 initial_contact 로그로 크기 조정 내역과 이후 관통을 확인합니다. 이전 Armature 자세 후보·측정 어깨 경사 fallback은 현재 SAM 크기 조정 경로에서 호출하지 않습니다.
garment_geometry의 실제 정점·엣지·면·표본 수와 자산 해시로 서버 옷 자산/버전을 확인할 수 있습니다.
기존 DB 피팅 경로의 시작 겹침은 강체 위치 이동·국소 보정·기준 모서리 길이를 유지하는 이웃 분산 보정으로 완화합니다. 현재 SAM 경로는 신체 크기 조정 후 중력 없이 안정화하며 최종 관통·치수·안정 기준을 충족하지 못하면 마지막 메시를 실패로 저장합니다.
SAM 몸통 크기는 별도 팔·손 윤곽을 제외한 닫힌 수평 단면에서 구합니다. 팔은 축에 수직인 실제 닫힌 윤곽의 면적 중심 offset과 두께를 분리하고 convex 윤곽에 10mm 여유를 준 방사 프로파일을 사용합니다. 상의는 signed clearance 9mm 미만 정점만 Blender Shrinkwrap OUTSIDE_SURFACE offset 10mm로 보정하며 몸통 프로파일 20mm 여유와 더 먼 정점은 유지합니다. 하의는 기존 <16mm → 20mm 정책을 유지합니다. 원본 SAM GLB는 변형하지 않습니다.
기준 엣지 늘어남 0.5%·수축 2% 또는 면 뒤집힘 한계를 넘으면 되돌립니다. SAM 경로에서 Cloth의 기준 형태는 신체 기준으로 크기를 조정한 옷입니다.
충돌 영역은 옷 경계에서 20cm 여유를 두고 선택합니다. 40% Decimate는 양방향 표본 오차 2mm 이내일 때만 사용합니다.
템플릿 FitMeSupport 또는 실제 경계 루프/어깨 앵커로 지지점을 생성합니다.
sam_collision_relaxation_v1은 자기 충돌(거리 1mm)을 사용합니다. 시작 rest에서 충돌 두께와 양립하지 않는 근접 면만 반응에서 제외하며 전체 최종 메시 검사는 유지합니다. 실제 소재 물성은 보장하지 않습니다.
SAM 크기 조정 내역은 별도 body_sizing에 기록합니다. Cloth에서 Shrinkwrap·압력·수축·봉제는 사용하지 않습니다.
0.5%를 넘는 정점 간 엣지 늘어남, 마지막 프레임 최대 이동 2mm 초과,
표본 관통 깊이 1mm 초과 결과는 실패로 판정하되 마지막 메시를 수정 없이 GLB로 저장합니다.
전체 삼각형 충돌의 수학적 보장은 아닙니다. 신체 GLB 원본·다운로드 URL은 의류 결과에 포함하지 않습니다.
실패 결과도 HTTP 200으로 전달하며 영수증은 status=error, preview_available=true와 검증된 모델 URL,
failure_reasons(stretch_exceeded/unsettled/body_penetration)를 포함합니다.
웹은 실패 상태를 유지하면서 저장된 옷을 표시합니다. simulation_status/failure_reasons는 GLB와 앵커에도 기록됩니다.
180초 예산·안정·발산을 감지해 조기 종료하며 시작/매 4프레임의 GLB 체크포인트를 유지합니다.
300초 강제 종료나 프로세스 오류 때 체크포인트가 있으면 simulation_timeout/simulation_interrupted 실패 미리보기를 게시합니다.
비유한 좌표는 마지막 유효 메시로 보존합니다. 체크포인트 이전 준비/내보내기 오류는 미리보기가 없을 수 있습니다.
initial_intersection/simulation_diverged/non_finite_simulation/simulation_incomplete도 실패 원인에 포함될 수 있습니다.
docker compose logs -f garment의 FITME_STAGE에서 준비·접촉·프레임·체크포인트·복구 단계를 확인할 수 있습니다.
첫 프레임 60초·이후 30초를 넘으면 부모 프로세스가 Blender를 종료하고 frame_timeout 실패 미리보기를 복구합니다.
의류 환경변수 CLOTH_FIRST_FRAME_TIMEOUT_SECONDS/CLOTH_FRAME_TIMEOUT_SECONDS로 조절합니다.
cloth_simulation.interruption은 중단 프레임·경과·제한시간이며 frames는 실제 저장된 프레임입니다.
국소 보정 거절은 pushout_rejected, 계산 영역 이탈은 collision_region_exited로 기록됩니다.
현재 SAM 경로는 fitme_garment.fitting_mode=sam_body_cloth_collision과 body_model_id로 결과를 식별합니다. 기존 db_cloth_collision 결과도 계속 읽습니다.
SAM 경로의 fitme_garment_measurements는 비우고 cloth_simulation.body_sizing에 신체 기준 조정 정보를 보존합니다. 신체 없는 기존 상품 크기 결과의 DB 케이지 보고서와 구분합니다.
웹은 성공 결과를 “SAM 신체 맞춤 3D”로 표시하고, 실패 결과에도 같은 모드 표시와 실패 상태를 유지합니다. sam_sizing_failed는 “SAM 신체 크기 맞춤 실패”로 표시하며 미리보기를 허용합니다. tryon-glb는 두 시뮬레이션 모드 모두 body_model_id가 신체 해시와 일치해야 합칩니다. FitStage도 새 모드를 서버 시뮬레이션으로 인식해 사진 속 팔 자세를 고정 45도 A 자세 검사로 거절하지 않습니다. 상품 실측 기반 사이즈 판정과 신체 맞춤 3D를 구분하며 관통을 작은 옷의 증거라고 설명하던 문구는 사용하지 않습니다.
실제 FitStage 표시 경로도 pair-files.verifiedModel에 현재 body_model_id를 전달해 신체 일치를 확인합니다. 신체를 다시 생성하면 이전 사이즈 교체 요청을 취소하고, 오래된 교체 응답은 현재 신체에 적용하지 않습니다.
SAM 경로에서 의류 생성·다운로드·해시/기준점 검증·착장 적용이 실패하면 DB 실측 근사 옷으로 대체하지 않습니다. 검증 가능한 실패 GLB는 실패 원인과 함께 그대로 표시하고, GLB가 없거나 검증할 수 없으면 신체만 표시하며 실제 오류와 재요청 안내를 알립니다. 사이즈 교체 실패 때도 이전 옷과 근사 옷을 제거합니다. 실측표 근사 옷은 예시 체형 미리보기에만 사용합니다. 상품 실측 기반 사이즈 판정은 그대로 유지합니다.
일반 촬영 경로는 3D 연결 확인을 기다린 뒤 시작합니다. 미설정·비로그인·카탈로그 미등록·연결 실패 상태에서는 사진 착장을 생성하지 않고 구체적인 오류와 재시도 안내를 표시하며 키·몸무게 판정만 제공합니다. 사진을 촬영했어도 이 상태에서 예시 신체·근사 옷으로 자동 전환하지 않습니다. 예시 신체와 근사 옷은 명시적인 `?loading=preview`에서만 사용합니다. 카메라 미리보기는 `object-fit: contain`으로 센서 프레임 전체를 표시하고 촬영 후에는 머리부터 양발까지 보이는지 확인하도록 안내합니다. 프런트 사진 처리는 크기·형식·용량만 검증하며 실제 전신 포함 여부 판정은 신체 API의 입력 검사 결과를 따릅니다.
의류 SQL의 연결 준비 중 일시 오류는 로그인 10초 실패 후 2초 대기하고 45초로 연결을 한 번 재시도합니다. 쿼리 실행·commit은 재시도하지 않습니다. 재연결도 실패하거나 OperationalError가 발생하면 의류 API는 ODBC 세부 정보 없이 HTTP 503 + Retry-After 5초를 반환합니다. 모델 생성이나 사이즈 판정의 SQL 준비 실패를 Blender 계산 오류와 구분하기 위한 처리입니다.
재질별 실측 물성은 아직 없으므로 결과는 검증 전 시뮬레이션입니다. Blender 제한시간은 300초입니다.
pair 워커 lease는 두 VM의 순차 요청 제한시간 합계보다 길게 설정해 실행 중인 작업의 중복 회수를 방지합니다.
body_model_id 없이 직접 호출하는 의류 API는 기존 상의 DB 실측 변형·하의 고정 원형 생성 경로를 유지합니다.
신체 내부에서는 SAM 복원 → 메시와 가이드의 동일 배율 키 보정 → SAM 정점/삼각형 직접 GLB 생성 순서입니다.

## 웹 배포 환경 설정

웹 VM의 미디어·pair 워커에도 다음 환경변수를 전달합니다. 통합 워커 구성은 웹 앱과 같은 환경을 사용합니다.
로컬 설정 파일은 web/.env이며 VM 배포 구성에서는 /opt/fitme-web/app.env에 동일한 값을 넣습니다.

```dotenv
BODY_MODEL_VM_URL=http://10.4.2.4:8001/api/avatars
GARMENT_MODEL_VM_URL=http://10.4.2.5:8002/api/garments
BODY_MODEL_BLOB_BASE=https://fitmemlstdev.blob.core.windows.net/body-glb
GARMENT_MODEL_BLOB_BASE=https://fitmemlstdev.blob.core.windows.net/garment-glb
MODEL_PAIR_VM_TIMEOUT_SECONDS=420
```

신체·의류 Compose는 각 VM의 .env에 VM_BIND_IP=10.4.2.4 또는 10.4.2.5를 설정합니다.
기본 loopback 바인딩으로는 다른 VM에서 접근할 수 없습니다. 인프라에서는 웹 VM 10.4.1.4에서
신체 8001·의류 8002로 통신하도록 네트워크를 설정해야 합니다.
브라우저는 웹 FastAPI의 같은 출처 /api 경로만 호출합니다. VM 주소와 ML 인증키를 브라우저에 넣지 않습니다.

로그인 프록시는 검증된 사용자 ID를 웹에 전달해야 합니다. 기존 ASGI 인증 미들웨어 또는
V2_MODEL_INGRESS_TOKEN을 사용하는 신뢰 프록시 방식을 유지합니다. 프록시 토큰은 브라우저에 넣지 않습니다.

## 웹 요청

`POST /api/v2/model-pair`, Content-Type: application/json

```json
{
  "body": {
    "height_cm": 175,
    "weight_kg": 70,
    "photo_b64": "JPEG 또는 PNG 파일의 Base64 본문",
    "photo_mime": "image/jpeg"
  },
  "garment": {"garment_id": 16, "size_id": 83}
}
```

사진은 3 MiB 이하이며 Data URL 접두사 없이 보냅니다. 상품·사이즈 ID는 실제 카탈로그에서 선택합니다.
JPEG/PNG 원본은 최대 6400만 화소까지 받고, 신체 서버가 EXIF 방향을 보정한 뒤
비율을 유지해 최대 1600만 화소로 줄여 SAM에 전달합니다. 3 MiB 용량 제한은 별도로 유지합니다.
저장된 매물은 garment 대신 `{"listing_id":"매물 ID"}` 객체를 사용할 수 있습니다.
사진·키·몸무게·사용자 ID는 URL 쿼리에 넣지 않습니다.

첫 응답은 HTTP 202입니다.

```json
{
  "job_id": "32자리 작업 ID",
  "status": "processing",
  "status_url": "/api/v2/model-pair/jobs/32자리 작업 ID"
}
```

같은 로그인 사용자로 status_url을 조회합니다. 처리 중에는 202, 완료되면 HTTP 200 결과를 받습니다.
한쪽 생성이 실패해도 결과 객체의 body·garment 각각에 ready 또는 error 상태가 있습니다.

## 웹으로 반환하는 것

```json
{
  "body": {
    "status": "ready",
    "model_id": "신체 GLB의 SHA-256",
    "glb_url": "신체 model.glb 읽기 링크",
    "anchors_url": "신체 anchors.json 읽기 링크",
    "measurements_url": "신체 measurements.json 읽기 링크"
  },
  "garment": {
    "status": "ready",
    "model_id": "의류 GLB의 SHA-256",
    "glb_url": "의류 model.glb 읽기 링크",
    "anchors_url": "의류 anchors.json 읽기 링크"
  }
}
```

- model.glb: 화면에 표시할 완성된 3D 모델입니다.
- anchors.json: 신체·옷의 위치와 방향을 맞추는 기준점입니다.
- measurements.json: 신체 모델의 목표·측정 치수 및 오차 보고서입니다. ML 입력 비율 파일이 아닙니다.
- model_id: 다운로드한 GLB가 맞는지 검사하는 해시입니다.

읽기 링크는 현재 15분 유효합니다. 브라우저가 Blob에서 직접 다운로드하므로 스토리지 CORS에
실제 웹 출처의 GET 접근을 허용해야 합니다. URL에 포함된 서명은 로그에 남기지 않습니다.
SAM 입력 치수 11개와 ML 인증키는 브라우저 응답에 포함하지 않습니다. 신체 치수 보고서는 변형한 기본 모델의 목표값·측정값·오차이며 surface는 template입니다.

사진은 웹의 만료되는 Redis 작업을 거쳐 신체 VM의 요청 임시 메모리 파일로 전달됩니다.
신체·ML 사이에는 SQL 저장이 없습니다. 완성된 모델과 보고서는 결과 Blob에 저장됩니다.

2026-11-12 최신 확인: 웹·의류·신체 VM은 실행 중입니다. 신체 VM에는 소스와 원본 네 모델을 준비했으나 SAM 추가 체크포인트·ML 모델이 없어 신체 API는 미기동 상태입니다.
웹 VM의 /opt/fitme-web/app.env와 실행 중인 앱 컨테이너에 네 연결 주소가 모두 일치함을 확인했습니다.
이미 적용되어 있어 파일 변경이나 컨테이너 재생성은 필요하지 않았습니다.
웹 /api/health는 HTTP 200·version 2, /api/v2/model-pair/status는 configured=true입니다.
웹에서 의류 API TCP 접근은 성공했고 신체 API는 서비스가 아직 기동되지 않아 접근되지 않습니다.
실제 GPU 생성·ML·Blob·웹 전체 연결은 추가 모델 준비와 서비스 배포 후 확인해야 합니다.

배포 담당자는 infra/deploy/web-3d-check.sh로 비밀 출력 없이 점검할 수 있습니다.
infra/deploy/web-3d-configure.sh는 네 주소만 적용하고 필요한 경우 기존 이미지로 app만 다시 생성합니다.
설정이 이미 일치하면 재시작하지 않으며, 적용 실패 시 이전 app.env로 복구합니다.
