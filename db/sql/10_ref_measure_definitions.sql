-- 치수 항목 정의 (표준 코드). body.measures / garment.measures 가 이 measure_code 를 참조
-- 허용값은 테이블_정의서/공통.xlsx 표준 용어 시트 (ref 는 시드로만 채우는 표라 CHECK 를 두지 않음)
CREATE TABLE IF NOT EXISTS ref.measure_definitions (
  measure_code  VARCHAR(50) PRIMARY KEY,   -- chest_girth, chest_width ...
  korean_name   VARCHAR(50),
  body_part     VARCHAR(10),               -- arm / leg / torso / neck / full
  measure_type  VARCHAR(10),               -- length / girth / height / breadth / depth
  basis         VARCHAR(10),               -- body(신체) / garment(옷 실측)
  iso_clause    VARCHAR(20) NULL           -- ISO 8559-1 조항 (모르면 NULL)
);
