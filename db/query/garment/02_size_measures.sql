-- 한 상품의 사이즈별 치수: basis=garment 는 옷 실측(value_cm), basis=body 는 권장 체형(low~high)
-- 바꿀 값: @garment_id
SET @garment_id = 1;

SELECT s.size_label, s.region, m.basis, m.measure_code, md.korean_name,
       m.value_cm, m.low_cm, m.high_cm
FROM garment.sizes AS s
JOIN garment.measures AS m ON m.size_id = s.size_id
JOIN ref.measure_definitions AS md ON md.measure_code = m.measure_code
WHERE s.garment_id = @garment_id
ORDER BY s.size_id, m.basis DESC, m.measure_code;   -- garment(실측) 먼저
