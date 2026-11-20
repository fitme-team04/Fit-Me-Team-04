-- 예시 데이터 (db/예시_데이터/ ref·body·garment.xlsx 와 같은 행). sql/ 초기화 뒤 수동 적재용이라 sql/ 밖에 둠 (init 자동 적용 안 됨)
-- 여러 번 실행해도 안전: 고정 id + INSERT ... ON DUPLICATE KEY UPDATE, FK 순서. MySQL 에서 실행 미검증 (정적 검사만)
-- 적재: docker exec -i -e MYSQL_PWD=poc-root poc-mysql mysql -uroot --default-character-set=utf8mb4 < db/sample/sample_data.sql
SET NAMES utf8mb4;

-- ref.measure_definitions (20행)
INSERT INTO ref.measure_definitions (measure_code, korean_name, body_part, measure_type, basis, iso_clause) VALUES
('height', '키', 'full', 'height', 'body', '5.1.1'),
('chest_girth', '가슴둘레', 'torso', 'girth', 'body', '5.3.4'),
('waist_girth', '허리둘레', 'torso', 'girth', 'body', '5.3.10'),
('stomach_girth', '배둘레', 'torso', 'girth', 'body', NULL),
('hip_girth', '엉덩이둘레', 'torso', 'girth', 'body', '5.3.13'),
('neck_girth', '목둘레', 'neck', 'girth', 'body', '5.3.2'),
('shoulder_width', '어깨너비', 'torso', 'length', 'body', '5.4.2'),
('arm_length', '팔길이', 'arm', 'length', 'body', NULL),
('inseam', '다리안쪽길이', 'leg', 'height', 'body', '5.1.15'),
('thigh_girth', '허벅지둘레', 'leg', 'girth', 'body', '5.3.20'),
('knee_girth', '무릎둘레', 'leg', 'girth', 'body', '5.3.22'),
('body_length', '총장', 'torso', 'length', 'garment', NULL),
('chest_width', '가슴단면', 'torso', 'breadth', 'garment', NULL),
('garment_shoulder_width', '어깨너비(옷)', 'torso', 'breadth', 'garment', NULL),
('sleeve_length', '소매길이', 'arm', 'length', 'garment', NULL),
('waist_width', '허리단면', 'torso', 'breadth', 'garment', NULL),
('hip_width', '엉덩이단면', 'torso', 'breadth', 'garment', NULL),
('thigh_width', '허벅지단면', 'leg', 'breadth', 'garment', NULL),
('knee_width', '무릎단면', 'leg', 'breadth', 'garment', NULL),
('garment_inseam', '안쪽기장', 'leg', 'length', 'garment', NULL)
AS new
ON DUPLICATE KEY UPDATE korean_name = new.korean_name, body_part = new.body_part, measure_type = new.measure_type, basis = new.basis, iso_clause = new.iso_clause;

-- ref.measure_aliases (20행)
INSERT INTO ref.measure_aliases (source_name, alias_name, measure_code) VALUES
('uniqlo_site', 'body-length-back', 'body_length'),
('uniqlo_site', 'body-width', 'chest_width'),
('uniqlo_site', 'shoulder-width', 'garment_shoulder_width'),
('uniqlo_site', 'sleeve-length-cb', 'sleeve_length'),
('uniqlo_site', 'nude-chest', 'chest_girth'),
('uniqlo_site', 'nude-waist', 'waist_girth'),
('musinsa_ml_project', '총장', 'body_length'),
('musinsa_ml_project', '가슴단면', 'chest_width'),
('musinsa_ml_project', '어깨너비', 'garment_shoulder_width'),
('musinsa_ml_project', '소매길이', 'sleeve_length'),
('kobo_garment_measurements', 'chest-width', 'chest_width'),
('kobo_garment_measurements', 'across-shoulder', 'garment_shoulder_width'),
('ansur2', 'stature', 'height'),
('ansur2', 'chestcircumference', 'chest_girth'),
('ansur2', 'waistcircumference', 'waist_girth'),
('ansur2', 'buttockcircumference', 'hip_girth'),
('ansur2', 'biacromialbreadth', 'shoulder_width'),
('bodym', 'chest', 'chest_girth'),
('bodym', 'waist', 'waist_girth'),
('bodym', 'hip', 'hip_girth')
AS new
ON DUPLICATE KEY UPDATE measure_code = new.measure_code;

-- ref.measure_maps (8행)
INSERT INTO ref.measure_maps (body_measure_code, garment_measure_code, factor) VALUES
('chest_girth', 'chest_width', 2.00),
('waist_girth', 'waist_width', 2.00),
('hip_girth', 'hip_width', 2.00),
('thigh_girth', 'thigh_width', 2.00),
('knee_girth', 'knee_width', 2.00),
('shoulder_width', 'garment_shoulder_width', 1.00),
('arm_length', 'sleeve_length', 1.00),
('inseam', 'garment_inseam', 1.00)
AS new
ON DUPLICATE KEY UPDATE factor = new.factor;

-- garment.brands (4행)
INSERT INTO garment.brands (brand_name, country, group_name) VALUES
('UNIQLO', 'JP', 'Fast Retailing'),
('GU', 'JP', 'Fast Retailing'),
('MUSINSA STANDARD', 'KR', 'Musinsa'),
('COVERNAT', 'KR', NULL)
AS new
ON DUPLICATE KEY UPDATE country = new.country, group_name = new.group_name;

-- body.users (5행)
INSERT INTO body.users (user_id, user_name, gender, birth_date, email) VALUES
(1, '예시사용자01', 'male', '1995-03-14', 'user01@example.com'),
(2, '예시사용자02', 'female', '1998-07-02', 'user02@example.com'),
(3, '예시사용자03', 'male', '1990-11-23', 'user03@example.com'),
(4, '예시사용자04', 'female', '2001-01-30', 'user04@example.com'),
(5, '예시사용자05', 'male', '1987-05-09', 'user05@example.com')
AS new
ON DUPLICATE KEY UPDATE user_name = new.user_name, gender = new.gender, birth_date = new.birth_date, email = new.email;

-- body.profiles (22행). body_type = 키·체중 BMI 의 대한비만학회 단계 (db/sql/24_body_profiles_body_type.sql)
-- user 18~22: 회원 1~5 더미 — 키·체중·치수는 ANSUR II 실제 대상자 값 (db/예시_데이터/body.xlsx 안내 시트에 SubjectId)
INSERT INTO body.profiles (profile_id, user_id, gender, age, height_cm, weight_kg, muscle_kg, body_fat_pct, body_type, source_name) VALUES
(1, NULL, 'male', 41, 177.6, 81.5, NULL, NULL, 'obese_1', 'ansur2'),
(2, NULL, 'male', 35, 170.2, 72.6, NULL, NULL, 'obese_1', 'ansur2'),
(3, NULL, 'male', 42, 173.5, 92.9, NULL, NULL, 'obese_2', 'ansur2'),
(4, NULL, 'male', 31, 165.5, 79.4, NULL, NULL, 'obese_1', 'ansur2'),
(5, NULL, 'male', 21, 191.4, 94.6, NULL, NULL, 'obese_1', 'ansur2'),
(6, NULL, 'female', 26, 156.0, 65.7, NULL, NULL, 'obese_1', 'ansur2'),
(7, NULL, 'female', 21, 166.5, 53.4, NULL, NULL, 'normal', 'ansur2'),
(8, NULL, 'female', 23, 171.1, 66.3, NULL, NULL, 'normal', 'ansur2'),
(9, NULL, 'female', 22, 166.0, 78.2, NULL, NULL, 'obese_1', 'ansur2'),
(10, NULL, 'female', 45, 157.2, 88.6, NULL, NULL, 'obese_3', 'ansur2'),
(11, NULL, 'female', NULL, 160.0, 92.4, NULL, NULL, 'obese_3', 'bodym'),
(12, NULL, 'female', NULL, 175.8, 102.8, NULL, NULL, 'obese_2', 'bodym'),
(13, NULL, 'male', NULL, 174.8, 106.9, NULL, NULL, 'obese_2', 'bodym'),
(14, NULL, 'male', NULL, 181.5, 111.8, NULL, NULL, 'obese_2', 'bodym'),
(15, NULL, 'female', NULL, 161.6, 93.0, NULL, NULL, 'obese_3', 'bodym'),
(16, NULL, 'female', NULL, 168.5, 97.6, NULL, NULL, 'obese_2', 'bodym'),
(17, NULL, 'male', NULL, 172.0, 104.4, NULL, NULL, 'obese_3', 'bodym'),
(18, 1, 'male', 31, 172.2, 62.5, NULL, NULL, 'normal', 'user'),
(19, 2, 'female', 28, 171.2, 79.1, NULL, NULL, 'obese_1', 'user'),
(20, 3, 'male', 35, 176.9, 75.6, NULL, NULL, 'pre_obese', 'user'),
(21, 4, 'female', 25, 171.3, 52.0, NULL, NULL, 'underweight', 'user'),
(22, 5, 'male', 39, 185.3, 109.4, NULL, NULL, 'obese_2', 'user')
AS new
ON DUPLICATE KEY UPDATE user_id = new.user_id, gender = new.gender, age = new.age, height_cm = new.height_cm, weight_kg = new.weight_kg, muscle_kg = new.muscle_kg, body_fat_pct = new.body_fat_pct, body_type = new.body_type, source_name = new.source_name;

-- body.measures (134행 — 20행 넘음: 더미 회원 5명 × ANSUR II 23항목 = 115행, ref.measure_aliases ansur2 전부, mm÷10)
INSERT INTO body.measures (profile_id, measure_code, value_cm, measure_method, model_version) VALUES
(1, 'height', 177.6, 'measured', NULL),
(1, 'chest_girth', 107.4, 'measured', NULL),
(1, 'waist_girth', 93.3, 'measured', NULL),
(1, 'hip_girth', 97.9, 'measured', NULL),
(1, 'shoulder_width', 40.1, 'measured', NULL),
(6, 'height', 156.0, 'measured', NULL),
(6, 'chest_girth', 92.2, 'measured', NULL),
(6, 'waist_girth', 85.0, 'measured', NULL),
(6, 'hip_girth', 101.1, 'measured', NULL),
(6, 'shoulder_width', 37.3, 'measured', NULL),
(11, 'chest_girth', 121.8, 'measured', NULL),
(11, 'waist_girth', 110.7, 'measured', NULL),
(11, 'hip_girth', 116.2, 'measured', NULL),
(12, 'chest_girth', 114.3, 'measured', NULL),
(12, 'waist_girth', 110.0, 'measured', NULL),
(12, 'hip_girth', 123.1, 'measured', NULL),
(13, 'chest_girth', 117.6, 'measured', NULL),
(13, 'waist_girth', 107.8, 'measured', NULL),
(13, 'hip_girth', 119.0, 'measured', NULL),
(18, 'height', 172.2, 'measured', NULL),
(18, 'chest_girth', 94.1, 'measured', NULL),
(18, 'waist_girth', 77.7, 'measured', NULL),
(18, 'hip_girth', 88.4, 'measured', NULL),
(18, 'neck_girth', 37.4, 'measured', NULL),
(18, 'shoulder_width', 42.9, 'measured', NULL),
(18, 'back_length', 46.2, 'measured', NULL),
(18, 'arm_length', 56.3, 'measured', NULL),
(18, 'upperarm_girth', 30.7, 'measured', NULL),
(18, 'wrist_girth', 16.6, 'measured', NULL),
(18, 'inseam', 82.4, 'measured', NULL),
(18, 'thigh_girth', 50.8, 'measured', NULL),
(18, 'calf_girth', 34.8, 'measured', NULL),
(18, 'ankle_girth', 21.2, 'measured', NULL),
(18, 'chest_height', 126.3, 'measured', NULL),
(18, 'waist_height', 102.9, 'measured', NULL),
(18, 'hip_height', 87.1, 'measured', NULL),
(18, 'chest_breadth', 28.7, 'measured', NULL),
(18, 'chest_depth', 20.7, 'measured', NULL),
(18, 'waist_breadth', 27.1, 'measured', NULL),
(18, 'waist_depth', 19.5, 'measured', NULL),
(18, 'hip_breadth', 31.2, 'measured', NULL),
(18, 'hip_depth', 19.7, 'measured', NULL),
(19, 'height', 171.2, 'measured', NULL),
(19, 'chest_girth', 100.7, 'measured', NULL),
(19, 'waist_girth', 95.8, 'measured', NULL),
(19, 'hip_girth', 106.3, 'measured', NULL),
(19, 'neck_girth', 34.3, 'measured', NULL),
(19, 'shoulder_width', 39.1, 'measured', NULL),
(19, 'back_length', 47.4, 'measured', NULL),
(19, 'arm_length', 59.0, 'measured', NULL),
(19, 'upperarm_girth', 30.9, 'measured', NULL),
(19, 'wrist_girth', 15.3, 'measured', NULL),
(19, 'inseam', 82.8, 'measured', NULL),
(19, 'thigh_girth', 64.9, 'measured', NULL),
(19, 'calf_girth', 38.3, 'measured', NULL),
(19, 'ankle_girth', 21.4, 'measured', NULL),
(19, 'chest_height', 122.2, 'measured', NULL),
(19, 'waist_height', 102.1, 'measured', NULL),
(19, 'hip_height', 88.9, 'measured', NULL),
(19, 'chest_breadth', 28.3, 'measured', NULL),
(19, 'chest_depth', 28.3, 'measured', NULL),
(19, 'waist_breadth', 32.2, 'measured', NULL),
(19, 'waist_depth', 25.1, 'measured', NULL),
(19, 'hip_breadth', 35.8, 'measured', NULL),
(19, 'hip_depth', 24.8, 'measured', NULL),
(20, 'height', 176.9, 'measured', NULL),
(20, 'chest_girth', 98.4, 'measured', NULL),
(20, 'waist_girth', 88.7, 'measured', NULL),
(20, 'hip_girth', 100.9, 'measured', NULL),
(20, 'neck_girth', 36.6, 'measured', NULL),
(20, 'shoulder_width', 41.0, 'measured', NULL),
(20, 'back_length', 48.5, 'measured', NULL),
(20, 'arm_length', 61.1, 'measured', NULL),
(20, 'upperarm_girth', 33.5, 'measured', NULL),
(20, 'wrist_girth', 17.0, 'measured', NULL),
(20, 'inseam', 85.2, 'measured', NULL),
(20, 'thigh_girth', 60.1, 'measured', NULL),
(20, 'calf_girth', 37.5, 'measured', NULL),
(20, 'ankle_girth', 22.4, 'measured', NULL),
(20, 'chest_height', 128.2, 'measured', NULL),
(20, 'waist_height', 107.6, 'measured', NULL),
(20, 'hip_height', 88.4, 'measured', NULL),
(20, 'chest_breadth', 26.4, 'measured', NULL),
(20, 'chest_depth', 23.6, 'measured', NULL),
(20, 'waist_breadth', 33.0, 'measured', NULL),
(20, 'waist_depth', 20.9, 'measured', NULL),
(20, 'hip_breadth', 35.3, 'measured', NULL),
(20, 'hip_depth', 23.7, 'measured', NULL),
(21, 'height', 171.3, 'measured', NULL),
(21, 'chest_girth', 76.6, 'measured', NULL),
(21, 'waist_girth', 65.7, 'measured', NULL),
(21, 'hip_girth', 92.3, 'measured', NULL),
(21, 'neck_girth', 29.9, 'measured', NULL),
(21, 'shoulder_width', 37.2, 'measured', NULL),
(21, 'back_length', 37.5, 'measured', NULL),
(21, 'arm_length', 56.6, 'measured', NULL),
(21, 'upperarm_girth', 25.0, 'measured', NULL),
(21, 'wrist_girth', 14.7, 'measured', NULL),
(21, 'inseam', 86.9, 'measured', NULL),
(21, 'thigh_girth', 53.7, 'measured', NULL),
(21, 'calf_girth', 31.1, 'measured', NULL),
(21, 'ankle_girth', 19.2, 'measured', NULL),
(21, 'chest_height', 128.6, 'measured', NULL),
(21, 'waist_height', 108.4, 'measured', NULL),
(21, 'hip_height', 89.9, 'measured', NULL),
(21, 'chest_breadth', 24.3, 'measured', NULL),
(21, 'chest_depth', 18.7, 'measured', NULL),
(21, 'waist_breadth', 22.1, 'measured', NULL),
(21, 'waist_depth', 17.6, 'measured', NULL),
(21, 'hip_breadth', 33.2, 'measured', NULL),
(21, 'hip_depth', 19.8, 'measured', NULL),
(22, 'height', 185.3, 'measured', NULL),
(22, 'chest_girth', 114.4, 'measured', NULL),
(22, 'waist_girth', 107.5, 'measured', NULL),
(22, 'hip_girth', 117.5, 'measured', NULL),
(22, 'neck_girth', 41.4, 'measured', NULL),
(22, 'shoulder_width', 45.3, 'measured', NULL),
(22, 'back_length', 52.5, 'measured', NULL),
(22, 'arm_length', 64.6, 'measured', NULL),
(22, 'upperarm_girth', 39.7, 'measured', NULL),
(22, 'wrist_girth', 17.8, 'measured', NULL),
(22, 'inseam', 89.2, 'measured', NULL),
(22, 'thigh_girth', 70.7, 'measured', NULL),
(22, 'calf_girth', 41.9, 'measured', NULL),
(22, 'ankle_girth', 23.8, 'measured', NULL),
(22, 'chest_height', 138.9, 'measured', NULL),
(22, 'waist_height', 113.5, 'measured', NULL),
(22, 'hip_height', 92.4, 'measured', NULL),
(22, 'chest_breadth', 28.9, 'measured', NULL),
(22, 'chest_depth', 29.2, 'measured', NULL),
(22, 'waist_breadth', 36.8, 'measured', NULL),
(22, 'waist_depth', 27.5, 'measured', NULL),
(22, 'hip_breadth', 38.8, 'measured', NULL),
(22, 'hip_depth', 29.0, 'measured', NULL)
AS new
ON DUPLICATE KEY UPDATE value_cm = new.value_cm, measure_method = new.measure_method, model_version = new.model_version;

-- body.poses (3행)
INSERT INTO body.poses (profile_id, ref_pose, arm_angle_deg, pelvis_tilt_deg, shoulder_tilt_deg) VALUES
(18, 'A', 45.0, 0.0, 0.0),
(19, 'A', 40.0, 1.5, -1.0),
(20, 'T', 90.0, 0.0, 0.5)
AS new
ON DUPLICATE KEY UPDATE ref_pose = new.ref_pose, arm_angle_deg = new.arm_angle_deg, pelvis_tilt_deg = new.pelvis_tilt_deg, shoulder_tilt_deg = new.shoulder_tilt_deg;

-- garment.garments (14행)
INSERT INTO garment.garments (garment_id, brand_id, source_name, item_code, garment_name, category, target_gender, fit) VALUES
(1, (SELECT brand_id FROM garment.brands WHERE brand_name = 'UNIQLO'), 'uniqlo_site', 'E465193-000', 'AIRism Cotton T-Shirt | Long Sleeve', '상의', 'unisex', NULL),
(2, (SELECT brand_id FROM garment.brands WHERE brand_name = 'UNIQLO'), 'uniqlo_site', 'E465760-000', 'Mini T-Shirt', '상의', 'female', NULL),
(3, (SELECT brand_id FROM garment.brands WHERE brand_name = 'UNIQLO'), 'uniqlo_site', 'E424873-000', '크루넥T', '상의', 'female', NULL),
(4, (SELECT brand_id FROM garment.brands WHERE brand_name = 'UNIQLO'), 'uniqlo_site', 'E487908-000', '립헨리넥T(긴팔)', '상의', 'female', NULL),
(5, (SELECT brand_id FROM garment.brands WHERE brand_name = 'UNIQLO'), 'uniqlo_site', 'E489040-000', 'Soft Ribbed T-Shirt | Long Sleeve | Stripe', '상의', 'female', NULL),
(6, (SELECT brand_id FROM garment.brands WHERE brand_name = 'UNIQLO'), 'uniqlo_site', 'E422992-000', '크루넥T', '상의', 'unisex', NULL),
(7, (SELECT brand_id FROM garment.brands WHERE brand_name = 'UNIQLO'), 'uniqlo_site', 'E487595-000', 'リブニットフリースVネックT', '상의', 'female', NULL),
(8, (SELECT brand_id FROM garment.brands WHERE brand_name = 'UNIQLO'), 'uniqlo_site', 'E470143-000', 'ソフトニットフリースクルーネックT', '상의', 'female', NULL),
(9, (SELECT brand_id FROM garment.brands WHERE brand_name = 'UNIQLO'), 'uniqlo_site', 'E487593-000', 'ソフトニットフリースハイネックT', '상의', 'female', NULL),
(10, (SELECT brand_id FROM garment.brands WHERE brand_name = 'UNIQLO'), 'uniqlo_site', 'E484336-000', 'ソフトニットフリースモックネックT', '상의', 'female', NULL),
(11, (SELECT brand_id FROM garment.brands WHERE brand_name = 'UNIQLO'), 'uniqlo_site', 'E465187-000', '드라이컬러크루넥T', '상의', 'male', NULL),
(12, (SELECT brand_id FROM garment.brands WHERE brand_name = 'UNIQLO'), 'uniqlo_site', 'E465751-000', '소프트립T(긴팔)', '상의', 'female', NULL),
(13, NULL, 'kobo_garment_measurements', 'mens-tops', 'mens-tops', '상의', 'male', NULL),
(14, (SELECT brand_id FROM garment.brands WHERE brand_name = 'COVERNAT'), 'musinsa_ml_project', '1848166', '에센셜 쿨 코튼 2-PACK 티셔츠 블랙', '상의', 'unisex', NULL)
AS new
ON DUPLICATE KEY UPDATE brand_id = new.brand_id, source_name = new.source_name, item_code = new.item_code, garment_name = new.garment_name, category = new.category, target_gender = new.target_gender, fit = new.fit;

-- garment.sizes (20행)
INSERT INTO garment.sizes (size_id, garment_id, size_label, region) VALUES
(1, 6, 'XS', 'KR'),
(2, 6, 'S', 'KR'),
(3, 6, 'M', 'KR'),
(4, 6, 'L', 'KR'),
(5, 6, 'XL', 'KR'),
(6, 6, 'XXL', 'KR'),
(7, 6, '3XL', 'KR'),
(8, 6, '4XL', 'KR'),
(9, 6, 'S', 'US'),
(10, 6, 'M', 'US'),
(11, 6, 'L', 'US'),
(12, 13, 'S', 'US'),
(13, 13, 'M', 'US'),
(14, 13, 'L', 'US'),
(15, 14, 'XS', 'KR'),
(16, 14, 'S', 'KR'),
(17, 14, 'M', 'KR'),
(18, 14, 'L', 'KR'),
(19, 14, 'XL', 'KR'),
(20, 14, 'XXL', 'KR')
AS new
ON DUPLICATE KEY UPDATE garment_id = new.garment_id, size_label = new.size_label, region = new.region;

-- garment.measures (18행)
INSERT INTO garment.measures (size_id, measure_code, basis, value_cm, low_cm, high_cm) VALUES
(3, 'body_length', 'garment', 69.0, NULL, NULL),
(3, 'garment_shoulder_width', 'garment', 46.5, NULL, NULL),
(3, 'chest_width', 'garment', 53.0, NULL, NULL),
(3, 'sleeve_length', 'garment', 45.0, NULL, NULL),
(3, 'chest_girth', 'body', NULL, 88.0, 96.0),
(3, 'waist_girth', 'body', NULL, 76.0, 84.0),
(10, 'body_length', 'garment', 72.0, NULL, NULL),
(10, 'garment_shoulder_width', 'garment', 48.0, NULL, NULL),
(10, 'chest_width', 'garment', 56.0, NULL, NULL),
(10, 'sleeve_length', 'garment', 47.0, NULL, NULL),
(10, 'chest_girth', 'body', NULL, 96.0, 104.0),
(10, 'waist_girth', 'body', NULL, 76.0, 84.0),
(13, 'chest_width', 'garment', 52.0, NULL, NULL),
(13, 'garment_shoulder_width', 'garment', 45.0, NULL, NULL),
(17, 'body_length', 'garment', 69.0, NULL, NULL),
(17, 'garment_shoulder_width', 'garment', 51.0, NULL, NULL),
(17, 'chest_width', 'garment', 55.0, NULL, NULL),
(17, 'sleeve_length', 'garment', 21.5, NULL, NULL)
AS new
ON DUPLICATE KEY UPDATE value_cm = new.value_cm, low_cm = new.low_cm, high_cm = new.high_cm;
