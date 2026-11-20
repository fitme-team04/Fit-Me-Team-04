-- 부위별 신체 치수 (팔 / 다리 / 몸통 / 목 뷰)
-- 바꿀 값: @profile_id. 필요한 부위 SELECT 만 실행해도 됨
SET @profile_id = 1;

SELECT measure_code, korean_name, measure_type, value_cm FROM body.arm_measures   WHERE profile_id = @profile_id;
SELECT measure_code, korean_name, measure_type, value_cm FROM body.leg_measures   WHERE profile_id = @profile_id;
SELECT measure_code, korean_name, measure_type, value_cm FROM body.torso_measures WHERE profile_id = @profile_id;
SELECT measure_code, korean_name, measure_type, value_cm FROM body.neck_measures  WHERE profile_id = @profile_id;
