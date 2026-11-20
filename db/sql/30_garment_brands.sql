-- 브랜드
CREATE TABLE IF NOT EXISTS garment.brands (
  brand_id    INT AUTO_INCREMENT PRIMARY KEY,
  brand_name  VARCHAR(50) UNIQUE,
  country     VARCHAR(5),                -- JP / KR ... (ISO 3166-1 두 글자)
  group_name  VARCHAR(50),               -- 모회사 (Fast Retailing ...)
  CONSTRAINT chk_brands_country CHECK (REGEXP_LIKE(country, '^[A-Z]{2}$', 'c'))
);
