-- 적재 점검: 스키마별 테이블 행 수 (정확한 COUNT)
-- 바꿀 값: 없음
SELECT 'ref'     AS schema_name, 'measure_definitions' AS table_name, COUNT(*) AS row_tally FROM ref.measure_definitions
UNION ALL SELECT 'ref',     'measure_aliases', COUNT(*) FROM ref.measure_aliases
UNION ALL SELECT 'ref',     'measure_maps',    COUNT(*) FROM ref.measure_maps
UNION ALL SELECT 'body',    'users',           COUNT(*) FROM body.users
UNION ALL SELECT 'body',    'profiles',        COUNT(*) FROM body.profiles
UNION ALL SELECT 'body',    'measures',        COUNT(*) FROM body.measures
UNION ALL SELECT 'body',    'poses',           COUNT(*) FROM body.poses
UNION ALL SELECT 'garment', 'brands',          COUNT(*) FROM garment.brands
UNION ALL SELECT 'garment', 'garments',        COUNT(*) FROM garment.garments
UNION ALL SELECT 'garment', 'sizes',           COUNT(*) FROM garment.sizes
UNION ALL SELECT 'garment', 'measures',        COUNT(*) FROM garment.measures;
