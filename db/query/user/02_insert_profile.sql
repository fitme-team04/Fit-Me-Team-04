-- 신체 정보 입력 (키·체중 등). 입력할 때마다 새 행 = 이력
-- 바꿀 값: @user_id 와 신체 값
-- body_type(체형)은 키·체중으로 계산: 대한비만학회 BMI 단계 (db/sql/24_body_profiles_body_type.sql, 예시_코드/_body_type.py 와 같은 규칙)
SET @user_id = 1;
SET @gender = 'male', @age = 30, @height_cm = 175.0, @weight_kg = 70.0, @muscle_kg = 32.0, @body_fat_pct = 18.0;
SET @bmi = @weight_kg / POW(@height_cm / 100, 2);
SET @body_type = CASE
  WHEN @bmi IS NULL THEN NULL
  WHEN @bmi < 18.5  THEN 'underweight'
  WHEN @bmi < 23    THEN 'normal'
  WHEN @bmi < 25    THEN 'pre_obese'
  WHEN @bmi < 30    THEN 'obese_1'
  WHEN @bmi < 35    THEN 'obese_2'
  ELSE 'obese_3'
END;

INSERT INTO body.profiles (user_id, gender, age, height_cm, weight_kg, muscle_kg, body_fat_pct, body_type, source_name)
VALUES (@user_id, @gender, @age, @height_cm, @weight_kg, @muscle_kg, @body_fat_pct, @body_type, 'user');

SELECT LAST_INSERT_ID() AS new_profile_id, @body_type AS body_type;   -- 다음 파일(03)의 @profile_id
