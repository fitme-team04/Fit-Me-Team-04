-- 신체 부위 치수 (실측 또는 AI 추정). 한 사람 × 한 항목 = 한 행
CREATE TABLE IF NOT EXISTS body.measures (
  profile_id      INT NOT NULL,
  measure_code    VARCHAR(50) NOT NULL,
  value_cm        DECIMAL(6,1),
  measure_method  VARCHAR(10),           -- measured / estimated
  model_version   VARCHAR(50) NULL,      -- estimated 일 때 모델 버전
  PRIMARY KEY (profile_id, measure_code),
  INDEX idx_measures_code (measure_code, value_cm),
  CONSTRAINT chk_measures_measure_method CHECK (measure_method IN ('measured', 'estimated')),
  FOREIGN KEY (profile_id)   REFERENCES body.profiles(profile_id),
  FOREIGN KEY (measure_code) REFERENCES ref.measure_definitions(measure_code)
);
