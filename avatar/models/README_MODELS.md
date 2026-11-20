# 신체 모델: Azure Blob 원본과 로컬 캐시

다음 네 원본은 **Azure Storage `fitmemlstdev` → `avatar-models`**에서 관리합니다.
Git에는 포함하지 않으며, 현재 저장소 폴더에서도 원본 파일을 제거했습니다.

| Blob 이름 | 역할 |
|---|---|
| `mhr_model.pt` | 원본 MHR 신체 리그 |
| `fitme_depth_fixed.blend` | FitMe 신체 변형용 Blender 원본 |
| `a_pose.npz` | 기준 A 포즈 |
| `sam_body.npz` | MHR와 FitMe 제어 메시의 바인딩 |

`bundled_assets.json`은 네 파일의 크기·SHA-256을 고정하는 Git 관리 명세입니다.
다운로드한 파일은 이 폴더의 Git 제외 캐시로 저장되고 API 컨테이너의 `/models`에 읽기 전용 연결됩니다.
모델 버전을 변경할 때는 호환되는 네 파일과 명세를 함께 갱신합니다.

## 실행

서비스 폴더에서 `.env.models.example`을 `.env.models`로 복사하고 관리 ID·SAS·연결 문자열 중 하나를 설정합니다.
`docker compose up --build -d`는 `model-sync`에서 다운로드·검증을 완료한 뒤 API를 시작합니다.
Docker 없이 사용할 때는 다음을 실행합니다.

```bash
python -m pip install -r requirements-models.txt
python scripts/download_blob_models.py --env-file .env.models
```

이미 크기·해시가 맞는 파일은 재사용하고, 임시 다운로드 검증에 실패하면 API 시작을 막습니다.
명령은 `avatar/`에서 실행합니다. 자세한 인증·운영 절차는 [DEPLOYMENT.md](../../docs/3d/DEPLOYMENT.md)를 따릅니다.

## Git에 남는 파일

- `bundled_assets.json`: 파일 크기·해시 및 출처 정보
- `a_pose.report.json`, `sam_body.report.json`: 생성·바인딩 보고서
- `sam_body.preview.glb`: 바인딩 확인용 미리보기
- `MHR_LICENSE.txt`: MHR 라이선스

SAM 사진 추론·ViTDet·MoGe 체크포인트는 별도 준비 대상이며 네 원본 모델 다운로드에 포함되지 않습니다.
외부 자산의 출처와 라이선스는 `../third_party/NOTICE.md` 및 라이선스 전문을 유지합니다.
