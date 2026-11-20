# 의류 서비스

실행·인증·SQL 절차는 [상위 배포 안내](../docs/3d/DEPLOYMENT.md)를 따릅니다.

- `src/api/`: HTTP API
- `src/core/`: 데이터 계약·작업 실행
- `src/geometry/`: 메시 변형·GLB·앵커
- `src/storage/`: 결과 Blob 및 모델 파일 검사
- `src/database/`: SQL 연결
- `src/checks/`: DB·생성 점검
- `web_viewer/`: Three.js 피팅 뷰어
- `scripts/`: 자산 준비 도구
- `models/`: 모델 명세·로컬 캐시
- `architecture/`: 구조와 파일 연결

외부 vendor 소스는 원본 라이선스와 코드를 유지합니다. validation/ 결과물은 포함하지 않습니다.
## 서버에 등록된 실제 템플릿 검사

컨테이너의 `GARMENT_TEMPLATE_DIR/registry.json`을 API와 똑같이 사용합니다. 기본 내장 모델로 바꾸지 않습니다.

```bash
docker compose exec garment /opt/blender/blender -b --factory-startup --python-exit-code 3 -P /app/scripts/check_registered_template.py
```

실패 요청의 DB 치수 JSON이 컨테이너에 있다면 끝에 `-- --spec-json /tmp/spec.json`을 추가합니다. `FITME_TEMPLATE_AUDIT`의 원본 해시·정점/삼각형 수가 서버 대상과 일치하는지 먼저 확인합니다. skinny_triangles는 경고이며, 실제 퇴화나 형상 악화·자기 교차·검사 미완료는 실패로 남습니다. 원본 .blend/.npz/registry는 수정하지 않습니다.
