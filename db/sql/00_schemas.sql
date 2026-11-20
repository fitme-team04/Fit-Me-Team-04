-- 스키마 3개: body(사람 치수) / garment(옷 치수) / ref(치수 항목 정의·대응)
-- 여러 번 실행해도 안전 (IF NOT EXISTS)
CREATE DATABASE IF NOT EXISTS body    CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE IF NOT EXISTS garment CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE IF NOT EXISTS ref     CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
