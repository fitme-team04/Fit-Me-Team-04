-- 역할: model-c 파이프라인 맨 위 Apply SQL Transformation (데이터셋 sizekorea_2021_adult2 → t1).
--       남자만, 입력 13개(키·몸무게 + SAM 11개)가 모두 있는 사람만 남기고 필요한 열만 고릅니다.
--       hip_depth_cm·upper_arm_girth_cm은 원본에 글자 형식으로 저장돼 있어 숫자로 바꿉니다.
--       (바꾸기 전 전체 MAE 1.66cm → 바꾼 뒤 1.60cm)
SELECT
  height_cm, weight_kg,
  inseam_cm, hip_girth_cm, hip_width_cm,
  CAST(hip_depth_cm AS REAL) AS hip_depth_cm,
  hip_line_height_cm, ankle_girth_cm, calf_girth_cm, knee_girth_cm, thigh_girth_cm,
  CAST(upper_arm_girth_cm AS REAL) AS upper_arm_girth_cm,
  wrist_girth_cm,
  torso_length_cm, shoulder_width_cm, arm_length_cm, waist_line_height_cm,
  chest_line_height_cm, belly_girth_cm, waist_girth_cm, waist_width_cm,
  waist_depth_cm, chest_girth_cm, chest_width_cm, chest_depth_cm,
  back_width_cm, underbust_girth_cm, belly_front_cm, hip_rear_cm, rise_arc_cm
FROM t1
WHERE gender = 'male'
  AND height_cm IS NOT NULL
  AND weight_kg IS NOT NULL
  AND inseam_cm IS NOT NULL
  AND hip_girth_cm IS NOT NULL
  AND hip_width_cm IS NOT NULL
  AND CAST(hip_depth_cm AS REAL) > 0
  AND hip_line_height_cm IS NOT NULL
  AND ankle_girth_cm IS NOT NULL
  AND calf_girth_cm IS NOT NULL
  AND knee_girth_cm IS NOT NULL
  AND thigh_girth_cm IS NOT NULL
  AND CAST(upper_arm_girth_cm AS REAL) > 0
  AND wrist_girth_cm IS NOT NULL
