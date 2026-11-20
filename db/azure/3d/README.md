# Azure SQL과 3D 카탈로그 연결

상품·실측은 기존 garment.garments/sizes/measures, 측정 정의·별칭은 ref.measure_definitions/measure_aliases를 재사용합니다.
별도 fitme_recipe 생성·등록 SQL은 제거했습니다.

2026-11-12 개발 DB fitme에서 레시피 테이블이 비어 있음을 확인하고 03 마이그레이션을 실행했습니다.
실행 후 OBJECT_ID 확인으로 테이블 제거를 검증했으며 상품·사이즈·실측·측정 사전은 변경하지 않았습니다.

API는 item_code·size_id로 조회하며 category가 상의이면 crewneck_v1, 하의이면 slacks_v1을 사용합니다.
소매 기준은 source_name에 해당하는 sleeve_length 별칭으로 정합니다.
DB에서 확인한 uniqlo_site의 sleeve-length-cb는 center_back, 표준 sleeve-length·소매길이·そで丈는 shoulder로 매핑합니다.
기준이 없거나 충돌하면 값을 추정하지 않고 거절합니다. body 기준 치수를 의류 실측으로 대체하지 않습니다.

`03_remove_recipe.sql`은 새 의류 코드 배포 후 빈 fitme.fitme_recipe만 제거합니다.
데이터가 추가돼 있으면 자동으로 중단하며 상품·실측 테이블은 변경하지 않습니다.
`02_migrate_legacy.sql`은 과거 서비스 객체를 위한 선택적 이관이며 레시피 테이블을 다시 만들거나 옮기지 않습니다.
`maintenance/`의 예제 복사 테이블 제거는 별도 검토용이며 이번 변경에서 실행하지 않습니다.

db/sql/의 기존 초기화 SQL은 MySQL용이므로 Azure SQL에서 그대로 실행하지 않습니다.

2026-11-12 신체·ML의 SQL 중계 방식을 취소하고 FastAPI JSON 직접 전달로 전환했습니다.
`04_remove_ml_feature_exchange.sql`로 생성했던 빈 임시 테이블과 전용 신체 VM SQL 사용자·권한을 제거했습니다.
상품·실측 테이블과 의류 VM 사용자는 유지했습니다. 신체·ML용 SQL 권한이나 만료 행 정리 작업은 필요하지 않습니다.
