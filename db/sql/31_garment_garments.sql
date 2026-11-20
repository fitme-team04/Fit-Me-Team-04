-- 옷 (상품 한 개). 인덱스는 테이블_정의서/garment.xlsx 인덱스 시트 기준
CREATE TABLE IF NOT EXISTS garment.garments (
  garment_id     INT AUTO_INCREMENT PRIMARY KEY,
  brand_id       INT,
  source_name    VARCHAR(50),            -- uniqlo_site / zozotown_page / kobo_garment_measurements ... (fetch 모듈 NAME)
  item_code      VARCHAR(50),            -- 출처의 상품번호 (출처 표기 그대로)
  garment_name   VARCHAR(200),
  category       VARCHAR(50),
  target_gender  VARCHAR(10),            -- male / female / unisex (옷의 대상 성별)
  fit            VARCHAR(20),            -- regular / slim / oversized ...
  UNIQUE KEY uq_garments_source (source_name, item_code),
  INDEX idx_garments_brand (brand_id, category, target_gender),
  CONSTRAINT chk_garments_source_name CHECK (REGEXP_LIKE(source_name, '^[a-z][a-z0-9_]*$', 'c')),
  CONSTRAINT chk_garments_target_gender CHECK (target_gender IN ('male', 'female', 'unisex')),
  CONSTRAINT chk_garments_fit CHECK (REGEXP_LIKE(fit, '^[a-z][a-z0-9_]*$', 'c')),
  FOREIGN KEY (brand_id) REFERENCES garment.brands(brand_id)
);
