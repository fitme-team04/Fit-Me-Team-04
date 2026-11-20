-- 역할: model-c 파이프라인 Split Data 아래 Apply SQL Transformation 2개 (학습용 왼쪽·시험용 오른쪽 모두 같은 쿼리).
--       예측 대상 17개를 item(어떤 치수인지) + value(값)로 세로로 쌓습니다.
--       Designer Train Model은 정답 열을 하나만 받기 때문에, 모델 하나가 17개를 모두 맞히도록 만든 형태입니다.
SELECT height_cm, weight_kg, inseam_cm, hip_girth_cm, hip_width_cm, hip_depth_cm, hip_line_height_cm, ankle_girth_cm, calf_girth_cm, knee_girth_cm, thigh_girth_cm, upper_arm_girth_cm, wrist_girth_cm, 'torso_length_cm' AS item, torso_length_cm AS value FROM t1 WHERE torso_length_cm IS NOT NULL
UNION ALL
SELECT height_cm, weight_kg, inseam_cm, hip_girth_cm, hip_width_cm, hip_depth_cm, hip_line_height_cm, ankle_girth_cm, calf_girth_cm, knee_girth_cm, thigh_girth_cm, upper_arm_girth_cm, wrist_girth_cm, 'shoulder_width_cm' AS item, shoulder_width_cm AS value FROM t1 WHERE shoulder_width_cm IS NOT NULL
UNION ALL
SELECT height_cm, weight_kg, inseam_cm, hip_girth_cm, hip_width_cm, hip_depth_cm, hip_line_height_cm, ankle_girth_cm, calf_girth_cm, knee_girth_cm, thigh_girth_cm, upper_arm_girth_cm, wrist_girth_cm, 'arm_length_cm' AS item, arm_length_cm AS value FROM t1 WHERE arm_length_cm IS NOT NULL
UNION ALL
SELECT height_cm, weight_kg, inseam_cm, hip_girth_cm, hip_width_cm, hip_depth_cm, hip_line_height_cm, ankle_girth_cm, calf_girth_cm, knee_girth_cm, thigh_girth_cm, upper_arm_girth_cm, wrist_girth_cm, 'waist_line_height_cm' AS item, waist_line_height_cm AS value FROM t1 WHERE waist_line_height_cm IS NOT NULL
UNION ALL
SELECT height_cm, weight_kg, inseam_cm, hip_girth_cm, hip_width_cm, hip_depth_cm, hip_line_height_cm, ankle_girth_cm, calf_girth_cm, knee_girth_cm, thigh_girth_cm, upper_arm_girth_cm, wrist_girth_cm, 'chest_line_height_cm' AS item, chest_line_height_cm AS value FROM t1 WHERE chest_line_height_cm IS NOT NULL
UNION ALL
SELECT height_cm, weight_kg, inseam_cm, hip_girth_cm, hip_width_cm, hip_depth_cm, hip_line_height_cm, ankle_girth_cm, calf_girth_cm, knee_girth_cm, thigh_girth_cm, upper_arm_girth_cm, wrist_girth_cm, 'belly_girth_cm' AS item, belly_girth_cm AS value FROM t1 WHERE belly_girth_cm IS NOT NULL
UNION ALL
SELECT height_cm, weight_kg, inseam_cm, hip_girth_cm, hip_width_cm, hip_depth_cm, hip_line_height_cm, ankle_girth_cm, calf_girth_cm, knee_girth_cm, thigh_girth_cm, upper_arm_girth_cm, wrist_girth_cm, 'waist_girth_cm' AS item, waist_girth_cm AS value FROM t1 WHERE waist_girth_cm IS NOT NULL
UNION ALL
SELECT height_cm, weight_kg, inseam_cm, hip_girth_cm, hip_width_cm, hip_depth_cm, hip_line_height_cm, ankle_girth_cm, calf_girth_cm, knee_girth_cm, thigh_girth_cm, upper_arm_girth_cm, wrist_girth_cm, 'waist_width_cm' AS item, waist_width_cm AS value FROM t1 WHERE waist_width_cm IS NOT NULL
UNION ALL
SELECT height_cm, weight_kg, inseam_cm, hip_girth_cm, hip_width_cm, hip_depth_cm, hip_line_height_cm, ankle_girth_cm, calf_girth_cm, knee_girth_cm, thigh_girth_cm, upper_arm_girth_cm, wrist_girth_cm, 'waist_depth_cm' AS item, waist_depth_cm AS value FROM t1 WHERE waist_depth_cm IS NOT NULL
UNION ALL
SELECT height_cm, weight_kg, inseam_cm, hip_girth_cm, hip_width_cm, hip_depth_cm, hip_line_height_cm, ankle_girth_cm, calf_girth_cm, knee_girth_cm, thigh_girth_cm, upper_arm_girth_cm, wrist_girth_cm, 'chest_girth_cm' AS item, chest_girth_cm AS value FROM t1 WHERE chest_girth_cm IS NOT NULL
UNION ALL
SELECT height_cm, weight_kg, inseam_cm, hip_girth_cm, hip_width_cm, hip_depth_cm, hip_line_height_cm, ankle_girth_cm, calf_girth_cm, knee_girth_cm, thigh_girth_cm, upper_arm_girth_cm, wrist_girth_cm, 'chest_width_cm' AS item, chest_width_cm AS value FROM t1 WHERE chest_width_cm IS NOT NULL
UNION ALL
SELECT height_cm, weight_kg, inseam_cm, hip_girth_cm, hip_width_cm, hip_depth_cm, hip_line_height_cm, ankle_girth_cm, calf_girth_cm, knee_girth_cm, thigh_girth_cm, upper_arm_girth_cm, wrist_girth_cm, 'chest_depth_cm' AS item, chest_depth_cm AS value FROM t1 WHERE chest_depth_cm IS NOT NULL
UNION ALL
SELECT height_cm, weight_kg, inseam_cm, hip_girth_cm, hip_width_cm, hip_depth_cm, hip_line_height_cm, ankle_girth_cm, calf_girth_cm, knee_girth_cm, thigh_girth_cm, upper_arm_girth_cm, wrist_girth_cm, 'back_width_cm' AS item, back_width_cm AS value FROM t1 WHERE back_width_cm IS NOT NULL
UNION ALL
SELECT height_cm, weight_kg, inseam_cm, hip_girth_cm, hip_width_cm, hip_depth_cm, hip_line_height_cm, ankle_girth_cm, calf_girth_cm, knee_girth_cm, thigh_girth_cm, upper_arm_girth_cm, wrist_girth_cm, 'underbust_girth_cm' AS item, underbust_girth_cm AS value FROM t1 WHERE underbust_girth_cm IS NOT NULL
UNION ALL
SELECT height_cm, weight_kg, inseam_cm, hip_girth_cm, hip_width_cm, hip_depth_cm, hip_line_height_cm, ankle_girth_cm, calf_girth_cm, knee_girth_cm, thigh_girth_cm, upper_arm_girth_cm, wrist_girth_cm, 'belly_front_cm' AS item, belly_front_cm AS value FROM t1 WHERE belly_front_cm IS NOT NULL
UNION ALL
SELECT height_cm, weight_kg, inseam_cm, hip_girth_cm, hip_width_cm, hip_depth_cm, hip_line_height_cm, ankle_girth_cm, calf_girth_cm, knee_girth_cm, thigh_girth_cm, upper_arm_girth_cm, wrist_girth_cm, 'hip_rear_cm' AS item, hip_rear_cm AS value FROM t1 WHERE hip_rear_cm IS NOT NULL
UNION ALL
SELECT height_cm, weight_kg, inseam_cm, hip_girth_cm, hip_width_cm, hip_depth_cm, hip_line_height_cm, ankle_girth_cm, calf_girth_cm, knee_girth_cm, thigh_girth_cm, upper_arm_girth_cm, wrist_girth_cm, 'rise_arc_cm' AS item, rise_arc_cm AS value FROM t1 WHERE rise_arc_cm IS NOT NULL
