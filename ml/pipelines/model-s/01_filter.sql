-- 역할: model-s 파이프라인 맨 위 Apply SQL Transformation (데이터셋 sizekorea_2021_adult2 → t1).
--       남자이고 키·몸무게가 있는 사람만 남깁니다. 항목별 결측은 02_stack.sql에서 항목마다 따로 뺍니다.
SELECT *
FROM t1
WHERE gender = 'male'
  AND height_cm IS NOT NULL
  AND weight_kg IS NOT NULL
