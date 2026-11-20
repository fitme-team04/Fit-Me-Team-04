-- 사이즈 추천(권장 체형): 브랜드가 준 권장 신체 범위(basis=body, low~high)에 내 치수가 드는지
-- 바꿀 값: @user_id, @garment_id. 범위 안 항목이 많은 사이즈가 위
SET @user_id = 1, @garment_id = 1;
SET @profile_id = (SELECT profile_id FROM body.profiles WHERE user_id = @user_id
                   ORDER BY created_at DESC, profile_id DESC LIMIT 1);

SELECT s.size_label, s.region,
       SUM(m1.value_cm BETWEEN m2.low_cm AND m2.high_cm) AS in_range_tally,
       COUNT(*) AS compared_tally,
       GROUP_CONCAT(CONCAT(m2.measure_code, ' ', m1.value_cm, ' (', m2.low_cm, '~', m2.high_cm, ')')
                    ORDER BY m2.measure_code SEPARATOR ', ') AS detail
FROM body.measures AS m1
JOIN garment.measures AS m2 ON m2.measure_code = m1.measure_code AND m2.basis = 'body'
JOIN garment.sizes AS s     ON s.size_id = m2.size_id
WHERE m1.profile_id = @profile_id
  AND s.garment_id = @garment_id
GROUP BY s.size_id, s.size_label, s.region
ORDER BY in_range_tally DESC, s.size_id;
