# 의류 모델 v19.1 (목 부분 재제작, 2026-11-25)

3D팀이 다시 만든 최종 의류 모델 원본입니다. 서비스에서 쓰던 Azure Blob(`fitmemlstdev/garment-models`)이 2026-11-20에 삭제되어, 같은 파일을 레포에 보관합니다.

| 파일 | 내용 |
|---|---|
| `body_center_back_v19.blend` / `.npz` | 크루넥 상의 (v19.1, 목 부분 재제작) |
| `black_midrise_straight_v1.blend` / `.npz` | 스트레이트 슬랙스 (v19와 같은 파일) |
| `registry.json` | 템플릿 ID, 기준 치수, 앵커 연결 정보 |

- 파일 이름·크기·SHA-256은 `../../bundled_garments.json`에 적혀 있고, 서버는 받은 파일이 이 값과 다르면 쓰지 않습니다. 파일을 수정하지 마세요.
- 폴더 경로는 `bundled_garments.json`의 `blob_prefix`와 같습니다. 다시 서비스하려면 이 폴더를 Blob `garment-models` 컨테이너에 같은 경로로 올리면 됩니다.
