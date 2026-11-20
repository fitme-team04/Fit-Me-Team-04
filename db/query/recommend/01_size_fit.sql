-- 사이즈 추천(항목별): 내 치수 ↔ measure_maps ↔ 옷 실측. 여유분 = 옷 × factor − 몸 (cm, 둘레 기준)
-- 바꿀 값: @user_id, @garment_id. 여유분이 음수면 그 항목은 작음
SET @user_id = 1, @garment_id = 1;
SET @profile_id = (SELECT profile_id FROM body.profiles WHERE user_id = @user_id
                   ORDER BY created_at DESC, profile_id DESC LIMIT 1);

SELECT s.size_label, s.region,
       mm.body_measure_code, m1.value_cm AS body_cm,
       mm.garment_measure_code, m2.value_cm AS garment_cm, mm.factor,
       ROUND(m2.value_cm * mm.factor - m1.value_cm, 1) AS ease_cm
FROM body.measures AS m1
JOIN ref.measure_maps AS mm   ON mm.body_measure_code = m1.measure_code
JOIN garment.measures AS m2   ON m2.measure_code = mm.garment_measure_code AND m2.basis = 'garment'
JOIN garment.sizes AS s       ON s.size_id = m2.size_id
WHERE m1.profile_id = @profile_id
  AND s.garment_id = @garment_id
ORDER BY s.size_id, mm.garment_measure_code;
