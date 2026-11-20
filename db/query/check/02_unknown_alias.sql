-- 적재 전 점검: 수집 파일의 측정명 중 ref.measure_aliases 에 없는 것 (있으면 51 시드에 추가 후 적재)
-- 바꿀 값: @source_name, @alias_names (수집 파일의 열 이름을 JSON 배열로 붙여넣기)
SET @source_name = 'ansur2';
SET @alias_names = '["stature", "chestcircumference", "footlength", "headcircumference"]';

SELECT jt.alias_name
FROM JSON_TABLE(@alias_names, '$[*]' COLUMNS (alias_name VARCHAR(100) PATH '$')) AS jt
LEFT JOIN ref.measure_aliases AS ma ON ma.source_name = @source_name AND ma.alias_name = jt.alias_name
WHERE ma.alias_name IS NULL;
