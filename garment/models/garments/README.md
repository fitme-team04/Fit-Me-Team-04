# 실제 의류 템플릿

- `crewneck_v1.blend` / `crewneck_v1.npz`: 기본 상의
- `slacks_v1.blend` / `slacks_v1.npz`: 기본 스트레이트 슬랙스
- `registry.json`: 템플릿 ID와 자산 연결, 기준 치수, 등록 결과

VM 상대 경로 `models/garments/` → 컨테이너 `/models/garments/` 읽기 전용 마운트.
실제 API는 이 `.blend`를 열고 기존 정점에 치수 변형을 적용합니다. UV 및 glTF 호환 재질을 내보냅니다.

기본 자산은 일반 형상이며 실제 브랜드 디자인의 복원이 아닙니다. 실상품 치수는 기존 garment 스키마에서 읽고, 레시피는 공통 db/azure/3d/에서 준비합니다.
팀의 다른 `.blend`는 `scripts/prepare_template.py`로 등록한 뒤 SQL `fitme_recipe.template_id`에 연결합니다. 자세한 좌표·치수·등록 명령은 `../../VM_GUIDE.md`를 참조하세요. 등록된 메시를 수정하면 새 ID로 재등록해야 합니다.

동봉 기본 자산은 상위 `models/` 제외 규칙에도 포함되도록 Git 예외 목록에 명시했습니다. 기본 파일은 모두 일반 Git이며 LFS가 필요하지 않습니다. 서비스 폴더의 `.gitignore`와 `.gitattributes`도 함께 커밋합니다. 추가 외부 자산은 원본 라이선스·용량 검토 후 별도 추적 규칙이 필요합니다. `build_templates.py`는 동봉 기본 자산을 다시 만드는 개발용 도구로, 기본 파일을 수정해 작업 중이라면 실행하지 마세요.
