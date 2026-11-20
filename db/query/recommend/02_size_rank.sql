-- 사이즈 추천(순위): 01 의 여유분을 사이즈별로 모아 정렬. 모든 항목 여유분 ≥ 0 인 사이즈 중 여유분이 가장 작은 것이 1순위
-- 바꿀 값: @user_id, @garment_id (PoC 단순 규칙 — 핏별 여유분 기준은 나중에)
SET @user_id = 1, @garment_id = 1;
SET @profile_id = (SELECT profile_id FROM body.profiles WHERE user_id = @user_id
                   ORDER BY created_at DESC, profile_id DESC LIMIT 1);

SELECT s.size_label, s.region,
       COUNT(*) AS compared_tally,
       MIN(ROUND(m2.value_cm * mm.factor - m1.value_cm, 1)) AS min_ease_cm,
       ROUND(AVG(m2.value_cm * mm.factor - m1.value_cm), 1)  AS avg_ease_cm,
       CASE WHEN MIN(m2.value_cm * mm.factor - m1.value_cm) >= 0 THEN 'fit' ELSE 'small' END AS size_status
FROM body.measures AS m1
JOIN ref.measure_maps AS mm   ON mm.body_measure_code = m1.measure_code
JOIN garment.measures AS m2   ON m2.measure_code = mm.garment_measure_code AND m2.basis = 'garment'
JOIN garment.sizes AS s       ON s.size_id = m2.size_id
WHERE m1.profile_id = @profile_id
  AND s.garment_id = @garment_id
GROUP BY s.size_id, s.size_label, s.region
ORDER BY (MIN(m2.value_cm * mm.factor - m1.value_cm) < 0), avg_ease_cm;
