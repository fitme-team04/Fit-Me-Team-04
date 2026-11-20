-- 사이즈별 치수. basis=garment 는 옷 실측(value_cm), basis=body 는 권장 신체 범위(low_cm~high_cm)
CREATE TABLE IF NOT EXISTS garment.measures (
  size_id       INT NOT NULL,
  measure_code  VARCHAR(50) NOT NULL,
  basis         VARCHAR(10) NOT NULL,    -- garment / body
  value_cm      DECIMAL(6,1) NULL,
  low_cm        DECIMAL(6,1) NULL,
  high_cm       DECIMAL(6,1) NULL,
  PRIMARY KEY (size_id, measure_code, basis),
  INDEX idx_measures_match (measure_code, basis, value_cm),   -- 내 치수에 맞는 옷 찾기
  CONSTRAINT chk_measures_basis CHECK (basis IN ('body', 'garment')),
  FOREIGN KEY (size_id)      REFERENCES garment.sizes(size_id),
  FOREIGN KEY (measure_code) REFERENCES ref.measure_definitions(measure_code)
);
