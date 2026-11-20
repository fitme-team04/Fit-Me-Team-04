# 신체 VM 배포·실제 생성 테스트

2026-11-12 신체 VM의 /opt/fitme-avatar에 현재 작업 소스와 비밀 없는 설정을 배포했습니다.
개인 .env와 키는 전송하지 않았습니다. GPU는 Tesla T4 16 GB, Docker는 실행 중입니다.
모델 다운로드용 격리 환경은 /opt/fitme-avatar/.venv-models입니다.
VM 호스트 Python 3.10에서도 해시 검증이 되도록 다운로드 도구를 수정했습니다.

## 완료한 실제 검사

- VM 실행 및 GPU 드라이버 확인
- 소스 묶음 SHA-256 검증 후 배치
- VM 관리 ID로 avatar-models 원본 4개 다운로드 및 크기·SHA-256 검증
- 파일 누락 시 모델을 빌드·기동하지 않고 중단하는 배포 사전 검사

원본 캐시는 /opt/fitme-avatar/models입니다. mhr_model.pt, fitme_depth_fixed.blend,
a_pose.npz, sam_body.npz가 준비됐습니다.

## 아직 필요한 실제 모델

| 파일·항목 | VM 배치 위치 |
| --- | --- |
| SAM checkpoint | models/sam/model.ckpt |
| SAM 설정 | models/sam/model_config.yaml |
| ViTDet 검출기 | models/vitdet/model_final_f05665.pkl |
| MoGe 모델 | models/moge/model.pt |
| Azure ML 모델·추론 코드 | Azure ML에 등록·배포, 신체 VM에는 설치하지 않음 |
| ML 연결 설정 | 신체 .env의 AZURE_ML_ENDPOINT·AZURE_ML_AUTH |

치수 예측기는 키·몸무게 및 실제 키에 맞춘 SAM cm 측정값 11개를 받아 키 제외 치수 28개를 출력하도록 학습·구현되어야 합니다. 계약 버전 2이며 기존 30개 입력 모델과 호환되지 않습니다.
SAM 추가 체크포인트는 scripts/download_models.py의 고정 리비전을 사용합니다.
승인된 Hugging Face 계정의 읽기 토큰을 VM의 비밀 환경으로 전달해야 하며 채팅·Git에 넣지 않습니다.
호스트에서 다운로드할 경우 .venv-models에 huggingface_hub를 설치한 후
`.venv-models/bin/python scripts/download_models.py --models /opt/fitme-avatar/models`를 실행합니다.
A 방식으로 Azure ML에 모델을 배포하고 AZURE_ML_ENDPOINT를 설정합니다. 기본 aad_token은 VM 관리 ID를 사용하며 호출 권한·네트워크는 별도 준비합니다.

## 준비 상태 확인과 기동

VM에서:

```bash
python3 /opt/fitme-avatar/deployment/body-readiness.py
cat /opt/fitme-avatar/deployment/readiness.json
bash /opt/fitme-avatar/deployment/body-start.sh
```

readiness.json에는 비밀값·사진·서명 URL이 없습니다. ready_to_start와 실제 API 실행 상태를 구분합니다. ml_endpoint_configured는 설정 형식 검사이며 실제 권한·통신·추론 성공은 아닙니다.
body-start.sh는 SAM 파일과 Azure ML 설정을 검사한 뒤 신체 API만 빌드·기동합니다. 로컬 ML 모델은 요구하지 않습니다.
기동 후 자산 호환성, 실제 GPU에서 SAM·검출기·MoGe·MHR 로딩, API health를 검사합니다.
파일 존재 확인만으로 실제 추론 성공을 판정하지 않습니다.

## 사진이 준비된 뒤 실제 생성·결과 검증

신뢰할 수 있는 웹 VM 또는 신체 VM에서 실제 계정 ID와 명시적으로 선택한 전신 사진으로 실행합니다.
이 테스트는 실제 생성 API를 사용하므로 성공하면 완성 모델이 body-glb에 저장됩니다.

```bash
python3 /opt/fitme-avatar/scripts/test_avatar_api.py \
  --photo /지정한/전신사진.jpg --height-cm 175 --weight-kg 70 \
  --subject 실제_테스트_계정_ID --output /새로운/비공개/결과폴더
```

--output은 존재하지 않는 새 폴더여야 합니다. 결과 폴더에는 model.glb, anchors.json,
measurements.json 및 test-result.json을 저장합니다. 서명 URL과 사진은 결과 보고서에 넣지 않습니다.
검증 항목은 GLB 해시·헤더, 모델 ID, GLB 내부 기준점·측정 보고서와 외부 JSON의 일치입니다.
실패 시 종료 코드 1과 정제된 실패 보고서를 남깁니다. 측정 정확도나 옷 피팅 품질은 별도 시각 검수가 필요합니다.

실제 추론·GLB 생성·결과 업로드에는 Azure ML 모델 배포·인증 설정과 명시적으로 지정한 테스트 사진이 필요합니다. 이번 A 방식 전환은 코드 변경이며 Azure 리소스 생성·VM 재배포는 미실행입니다.
웹 연결 주소 설정은 완료됐지만 신체 API가 기동되기 전에는 웹에서 실제 생성할 수 없습니다.
