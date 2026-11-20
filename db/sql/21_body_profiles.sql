-- 신체 정보 (사용자 입력 또는 데이터셋 한 명). 인덱스는 테이블_정의서/body.xlsx 인덱스 시트 기준
CREATE TABLE IF NOT EXISTS body.profiles (
  profile_id    INT AUTO_INCREMENT PRIMARY KEY,
  user_id       INT NULL,                -- NULL = 데이터셋 행 (ansur2 / bodym ...)
  gender        VARCHAR(10),             -- male / female
  age           INT,
  height_cm     DECIMAL(5,1),
  weight_kg     DECIMAL(5,1),
  muscle_kg     DECIMAL(5,1),
  body_fat_pct  DECIMAL(4,1),
  source_name   VARCHAR(50),             -- user / ansur2 / bodym ... (fetch 모듈 NAME)
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_profiles_user (user_id),
  INDEX idx_profiles_source (source_name),
  INDEX idx_profiles_body (gender, height_cm, weight_kg),   -- 등호(gender) 먼저, 범위(height_cm) 다음
  CONSTRAINT chk_profiles_gender CHECK (gender IN ('male', 'female')),
  CONSTRAINT chk_profiles_source_name CHECK (REGEXP_LIKE(source_name, '^[a-z][a-z0-9_]*$', 'c')),
  FOREIGN KEY (user_id) REFERENCES body.users(user_id)
);
