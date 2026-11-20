-- body.profiles 에 체형(body_type) 컬럼 추가. 21_ 의 CREATE 는 그대로 두고 컬럼 변경은 새 파일로 (CHANGELOG 규칙)
-- 값: 대한비만학회(KSSO) 비만 진료지침 2022 8판 요약본 표 1 "한국인에서 체질량지수와 허리둘레에 따른 비만 동반 질환 위험도"
--   https://general.kosso.or.kr/html/user/core/view/reaction/main/kosso/inc/data/guideline2022_vol8.pdf
--   underweight 저체중 BMI < 18.5 / normal 정상 18.5~22.9 / pre_obese 비만전단계 23~24.9
--   obese_1 1단계 비만 25~29.9 / obese_2 2단계 비만 30~34.9 / obese_3 3단계 비만 ≥ 35   (BMI = 체중 kg / (키 m)²)
-- 여러 번 실행해도 안전: MySQL 8.0 에는 ADD COLUMN IF NOT EXISTS 가 없어 information_schema 로 확인 후 PREPARE/EXECUTE
--   (없을 때만 ALTER, 있으면 DO 0 = 아무것도 안 함, 출력도 없음)

-- 1) 컬럼 (body_fat_pct 다음)
SET @sql = IF(
  (SELECT COUNT(*) FROM information_schema.columns
   WHERE table_schema = 'body' AND table_name = 'profiles' AND column_name = 'body_type') = 0,
  'ALTER TABLE body.profiles ADD COLUMN body_type VARCHAR(20) NULL AFTER body_fat_pct',
  'DO 0');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2) CHECK 제약 (허용값 또는 NULL — NULL IN (...) 은 NULL 이라 CHECK 를 통과)
SET @sql = IF(
  (SELECT COUNT(*) FROM information_schema.table_constraints
   WHERE constraint_schema = 'body' AND table_name = 'profiles'
     AND constraint_name = 'chk_profiles_body_type' AND constraint_type = 'CHECK') = 0,
  'ALTER TABLE body.profiles ADD CONSTRAINT chk_profiles_body_type CHECK (body_type IN (''underweight'', ''normal'', ''pre_obese'', ''obese_1'', ''obese_2'', ''obese_3''))',
  'DO 0');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
