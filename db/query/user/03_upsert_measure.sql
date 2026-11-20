-- 신체 부위 치수 입력·수정 (실측 measured / AI 추정 estimated)
-- 바꿀 값: @profile_id, 아래 VALUES 줄 (measure_code 는 ref.measure_definitions 의 measure_code)
SET @profile_id = 1;

INSERT INTO body.measures (profile_id, measure_code, value_cm, measure_method, model_version) VALUES
(@profile_id, 'chest_girth',    96.0, 'measured', NULL),
(@profile_id, 'waist_girth',    82.0, 'measured', NULL),
(@profile_id, 'shoulder_width', 45.0, 'measured', NULL),
(@profile_id, 'arm_length',     60.0, 'measured', NULL)
AS new
ON DUPLICATE KEY UPDATE value_cm = new.value_cm, measure_method = new.measure_method, model_version = new.model_version;

SELECT * FROM body.measures WHERE profile_id = @profile_id;
