-- AI 학습 데이터: 1명 = 1행으로 펼치기 (조건부 집계). 없는 항목은 NULL
-- 바꿀 값: @source_name (ansur2 / bodym / user, NULL 이면 전체). 열을 늘리려면 MAX(CASE ...) 줄 복사
SET @source_name = NULL;

SELECT p.profile_id, p.source_name, p.gender, p.age, p.height_cm, p.weight_kg,
       MAX(CASE WHEN m.measure_code = 'chest_girth'    THEN m.value_cm END) AS chest_girth,
       MAX(CASE WHEN m.measure_code = 'waist_girth'    THEN m.value_cm END) AS waist_girth,
       MAX(CASE WHEN m.measure_code = 'hip_girth'      THEN m.value_cm END) AS hip_girth,
       MAX(CASE WHEN m.measure_code = 'neck_girth'     THEN m.value_cm END) AS neck_girth,
       MAX(CASE WHEN m.measure_code = 'shoulder_width' THEN m.value_cm END) AS shoulder_width,
       MAX(CASE WHEN m.measure_code = 'arm_length'     THEN m.value_cm END) AS arm_length,
       MAX(CASE WHEN m.measure_code = 'upperarm_girth' THEN m.value_cm END) AS upperarm_girth,
       MAX(CASE WHEN m.measure_code = 'wrist_girth'    THEN m.value_cm END) AS wrist_girth,
       MAX(CASE WHEN m.measure_code = 'inseam'         THEN m.value_cm END) AS inseam,
       MAX(CASE WHEN m.measure_code = 'thigh_girth'    THEN m.value_cm END) AS thigh_girth,
       MAX(CASE WHEN m.measure_code = 'calf_girth'     THEN m.value_cm END) AS calf_girth,
       MAX(CASE WHEN m.measure_code = 'ankle_girth'    THEN m.value_cm END) AS ankle_girth
FROM body.profiles AS p
JOIN body.measures AS m ON m.profile_id = p.profile_id
WHERE (@source_name IS NULL OR p.source_name = @source_name)
  AND m.measure_method = 'measured'    -- 학습에는 실측값만 (AI 추정값 제외)
GROUP BY p.profile_id
ORDER BY p.profile_id;
