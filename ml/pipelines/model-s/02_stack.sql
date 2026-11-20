-- 역할: model-s 파이프라인 Split Data 아래 Apply SQL Transformation 2개 (학습용·시험용 같은 쿼리).
--       키·몸무게만 입력으로, SAM 11개를 item + value로 세로로 쌓습니다.
--       값을 REAL로 바꾸고 0 이하·빈 값을 빼서, 글자 형식으로 저장된 열이 섞여도 학습이 깨지지 않게 합니다.
SELECT height_cm, weight_kg, 'inseam_cm' AS item, CAST(inseam_cm AS REAL) AS value FROM t1 WHERE CAST(inseam_cm AS REAL) > 0
UNION ALL
SELECT height_cm, weight_kg, 'hip_girth_cm' AS item, CAST(hip_girth_cm AS REAL) AS value FROM t1 WHERE CAST(hip_girth_cm AS REAL) > 0
UNION ALL
SELECT height_cm, weight_kg, 'hip_width_cm' AS item, CAST(hip_width_cm AS REAL) AS value FROM t1 WHERE CAST(hip_width_cm AS REAL) > 0
UNION ALL
SELECT height_cm, weight_kg, 'hip_depth_cm' AS item, CAST(hip_depth_cm AS REAL) AS value FROM t1 WHERE CAST(hip_depth_cm AS REAL) > 0
UNION ALL
SELECT height_cm, weight_kg, 'hip_line_height_cm' AS item, CAST(hip_line_height_cm AS REAL) AS value FROM t1 WHERE CAST(hip_line_height_cm AS REAL) > 0
UNION ALL
SELECT height_cm, weight_kg, 'ankle_girth_cm' AS item, CAST(ankle_girth_cm AS REAL) AS value FROM t1 WHERE CAST(ankle_girth_cm AS REAL) > 0
UNION ALL
SELECT height_cm, weight_kg, 'calf_girth_cm' AS item, CAST(calf_girth_cm AS REAL) AS value FROM t1 WHERE CAST(calf_girth_cm AS REAL) > 0
UNION ALL
SELECT height_cm, weight_kg, 'knee_girth_cm' AS item, CAST(knee_girth_cm AS REAL) AS value FROM t1 WHERE CAST(knee_girth_cm AS REAL) > 0
UNION ALL
SELECT height_cm, weight_kg, 'thigh_girth_cm' AS item, CAST(thigh_girth_cm AS REAL) AS value FROM t1 WHERE CAST(thigh_girth_cm AS REAL) > 0
UNION ALL
SELECT height_cm, weight_kg, 'upper_arm_girth_cm' AS item, CAST(upper_arm_girth_cm AS REAL) AS value FROM t1 WHERE CAST(upper_arm_girth_cm AS REAL) > 0
UNION ALL
SELECT height_cm, weight_kg, 'wrist_girth_cm' AS item, CAST(wrist_girth_cm AS REAL) AS value FROM t1 WHERE CAST(wrist_girth_cm AS REAL) > 0
