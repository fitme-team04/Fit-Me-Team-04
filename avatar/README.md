> Current policy: Blender is NOT resident. Only verified model files stay cached on disk; each Blender job starts and exits independently. See blender-oneshot.md. Earlier resident descriptions below are historical.

# 신체 아바타 서비스

기본 사진 API는 SAM A 자세 메시를 입력 키에 맞춰 동일 배율로 보정한 뒤 직접 GLB로 내보냅니다.
기본 모델은 부위/앵커 가이드에만 사용하며 ML 예측으로 최종 신체를 변형하지 않습니다.
`.env`의 `FITME_ML_MEASUREMENTS=on`(기본 off)으로 Azure ML 치수 28개를 핏 판정용 `target`으로 붙일 수 있습니다.
웹 표시와 의류 Collision에 같은 SAM GLB를 사용합니다.

실행·인증·SQL 절차는 [상위 배포 안내](../docs/3d/DEPLOYMENT.md)를 따릅니다.

- `src/api/`: HTTP API
- `src/core/`: 데이터 계약·작업 실행
- `src/geometry/`: 메시 변형·GLB·앵커
- `src/storage/`: 결과 Blob 및 모델 파일 검사
- `src/inference/`: SAM 사진 추론
- `azureml/`: 키·몸무게 기반 ML 배포
- `scripts/`: 자산 준비 도구
- `models/`: 모델 명세·로컬 캐시
- `architecture/`: 구조와 파일 연결

외부 vendor 소스는 원본 라이선스와 코드를 유지합니다. validation/ 결과물은 포함하지 않습니다.


Body Blender runs per request with independent copies; see [current policy](docs/blender-oneshot.md).
