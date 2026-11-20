-- 사용자 (기본 정보 + 가입 시각)
CREATE TABLE IF NOT EXISTS body.users (
  user_id     INT AUTO_INCREMENT PRIMARY KEY,
  user_name   VARCHAR(50),
  gender      VARCHAR(10),               -- male / female
  birth_date  DATE,                      -- 나이는 여기서 계산
  email       VARCHAR(100) UNIQUE,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,   -- 가입 시각
  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT chk_users_gender CHECK (gender IN ('male', 'female'))
);
