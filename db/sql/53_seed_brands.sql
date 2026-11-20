-- 시드(초안): 브랜드 (brand_name UNIQUE 로 중복 방지)
INSERT INTO garment.brands (brand_name, country, group_name) VALUES
('UNIQLO',           'JP', 'Fast Retailing'),
('GU',               'JP', 'Fast Retailing'),
('MUSINSA STANDARD', 'KR', 'Musinsa'),
('COVERNAT',         'KR', NULL)
AS new
ON DUPLICATE KEY UPDATE country = new.country, group_name = new.group_name;
