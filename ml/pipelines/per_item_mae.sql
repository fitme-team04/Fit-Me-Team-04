-- 역할: model-c·model-s 공통. Score Model 아래 Apply SQL Transformation으로 항목별 평균 절대 오차(cm)를 계산합니다.
--       Evaluate Model의 전체 MAE·R²는 항목이 섞여 있어 R²가 부풀려지므로, 항목별 오차를 성능 기준으로 씁니다.
SELECT
  item,
  COUNT(*) AS n,
  ROUND(AVG(ABS(value - "Scored Labels")), 2) AS mae_cm
FROM t1
GROUP BY item
ORDER BY mae_cm DESC
