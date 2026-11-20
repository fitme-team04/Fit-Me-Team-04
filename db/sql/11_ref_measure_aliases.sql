-- 출처별 항목 이름 → 표준 코드 변환표 (수집 데이터 적재 시 사용)
CREATE TABLE IF NOT EXISTS ref.measure_aliases (
  source_name   VARCHAR(50)  NOT NULL,   -- uniqlo_site / ansur2 / bodym ... (fetch 모듈 NAME)
  alias_name    VARCHAR(100) NOT NULL,   -- 출처에서 쓰는 원래 이름 (출처 표기 그대로)
  measure_code  VARCHAR(50)  NOT NULL,
  PRIMARY KEY (source_name, alias_name),
  FOREIGN KEY (measure_code) REFERENCES ref.measure_definitions(measure_code)
);
