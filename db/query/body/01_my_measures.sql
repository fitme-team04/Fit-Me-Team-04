-- 한 사람의 신체 치수 전체 (가장 최근 신체 정보 기준)
-- 바꿀 값: @user_id
SET @user_id = 1;
SET @profile_id = (SELECT profile_id FROM body.profiles WHERE user_id = @user_id
                   ORDER BY created_at DESC, profile_id DESC LIMIT 1);

SELECT p.profile_id, p.gender, p.age, p.height_cm, p.weight_kg, p.created_at
FROM body.profiles AS p WHERE p.profile_id = @profile_id;

SELECT body_part, measure_type, measure_code, korean_name, value_cm, measure_method
FROM body.measure_details
WHERE profile_id = @profile_id
ORDER BY body_part, measure_type, measure_code;
