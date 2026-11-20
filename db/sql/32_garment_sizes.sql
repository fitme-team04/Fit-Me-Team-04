-- 옷 사이즈 (상품 × 사이즈 표기 × 지역)
CREATE TABLE IF NOT EXISTS garment.sizes (
  size_id     INT AUTO_INCREMENT PRIMARY KEY,
  garment_id  INT NOT NULL,
  size_label  VARCHAR(20),               -- S / M / 95 / 28 ... (출처 표기 그대로)
  region      VARCHAR(5),                -- KR / JP / US / EU / INT ... (사이즈 표기 체계)
  UNIQUE KEY uq_sizes_garment (garment_id, size_label, region),   -- FK 인덱스 겸용
  CONSTRAINT chk_sizes_region CHECK (REGEXP_LIKE(region, '^[A-Z]{2,5}$', 'c')),
  FOREIGN KEY (garment_id) REFERENCES garment.garments(garment_id)
);
