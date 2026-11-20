-- 적재 점검: 치수가 하나도 없는 사이즈, 값이 모두 비어 있는 치수 행
-- 바꿀 값: 없음
SELECT g.garment_id, g.source_name, g.item_code, s.size_id, s.size_label, s.region
FROM garment.sizes AS s
JOIN garment.garments AS g ON g.garment_id = s.garment_id
LEFT JOIN garment.measures AS m ON m.size_id = s.size_id
WHERE m.size_id IS NULL
ORDER BY g.garment_id, s.size_id;

SELECT m.size_id, m.measure_code, m.basis
FROM garment.measures AS m
WHERE m.value_cm IS NULL AND m.low_cm IS NULL AND m.high_cm IS NULL;
