-- 출처별 항목 채움 현황: 어떤 항목을 학습 열로 쓸 수 있는지 (인원 수·평균·범위)
-- 바꿀 값: 없음 (전체 출처)
SELECT p.source_name, m.measure_code,
       COUNT(*) AS profile_tally,
       ROUND(AVG(m.value_cm), 1) AS avg_cm,
       MIN(m.value_cm) AS min_cm,
       MAX(m.value_cm) AS max_cm
FROM body.profiles AS p
JOIN body.measures AS m ON m.profile_id = p.profile_id
WHERE m.measure_method = 'measured'
GROUP BY p.source_name, m.measure_code
ORDER BY p.source_name, profile_tally DESC, m.measure_code;
