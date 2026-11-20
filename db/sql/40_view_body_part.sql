-- 신체 치수 + 항목 정의(부위·종류) 뷰, 그리고 부위별 뷰
CREATE OR REPLACE VIEW body.measure_details AS
SELECT m.profile_id, m.measure_code, md.korean_name, md.body_part, md.measure_type,
       m.value_cm, m.measure_method, m.model_version
FROM body.measures AS m
JOIN ref.measure_definitions AS md ON md.measure_code = m.measure_code;

CREATE OR REPLACE VIEW body.arm_measures   AS SELECT * FROM body.measure_details WHERE body_part = 'arm';
CREATE OR REPLACE VIEW body.leg_measures   AS SELECT * FROM body.measure_details WHERE body_part = 'leg';
CREATE OR REPLACE VIEW body.torso_measures AS SELECT * FROM body.measure_details WHERE body_part = 'torso';
CREATE OR REPLACE VIEW body.neck_measures  AS SELECT * FROM body.measure_details WHERE body_part = 'neck';
