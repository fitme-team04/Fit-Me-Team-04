-- 신체 치수 ↔ 옷 치수 대응 규칙 (예: 가슴둘레 = 가슴단면 × 2)
-- 두 FK 가 같은 measure_definitions 를 가리키므로 역할 이름(body_ / garment_)을 붙임
CREATE TABLE IF NOT EXISTS ref.measure_maps (
  body_measure_code     VARCHAR(50) NOT NULL,
  garment_measure_code  VARCHAR(50) NOT NULL,
  factor                DECIMAL(4,2),          -- 신체값 ≈ 옷값 × factor
  PRIMARY KEY (body_measure_code, garment_measure_code),
  FOREIGN KEY (body_measure_code)    REFERENCES ref.measure_definitions(measure_code),
  FOREIGN KEY (garment_measure_code) REFERENCES ref.measure_definitions(measure_code)
);
