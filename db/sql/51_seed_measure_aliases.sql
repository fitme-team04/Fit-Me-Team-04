-- 시드(초안): 출처별 항목 이름 → 표준 코드. 정의가 완전히 같지 않은 것은 주석
-- source_name 은 fetch 모듈 NAME(밑줄), alias_name 은 출처 표기 그대로(하이픈·대소문자 유지)
INSERT INTO ref.measure_aliases (source_name, alias_name, measure_code) VALUES
-- 유니클로 사이트
('uniqlo_site', 'body-length-back',  'body_length'),
('uniqlo_site', 'body-width',        'chest_width'),
('uniqlo_site', 'shoulder-width',    'garment_shoulder_width'),
('uniqlo_site', 'sleeve-length-cb',  'sleeve_length'),   -- 목 뒤 중심 기준 (화장), 어깨 끝 기준과 다름
('uniqlo_site', 'nude-chest',        'chest_girth'),
('uniqlo_site', 'nude-bust',         'chest_girth'),
('uniqlo_site', 'nude-waist',        'waist_girth'),
('uniqlo_site', 'nude-hip',          'hip_girth'),
('uniqlo_site', 'nude-height',       'height'),
-- 무신사 (ML 프로젝트 수집본)
('musinsa_ml_project', '총장',       'body_length'),
('musinsa_ml_project', '가슴단면',   'chest_width'),
('musinsa_ml_project', '어깨너비',   'garment_shoulder_width'),
('musinsa_ml_project', '소매길이',   'sleeve_length'),
-- ZOZOTOWN
('zozotown_page', '着丈',    'body_length'),
('zozotown_page', '身幅',    'chest_width'),
('zozotown_page', '肩幅',    'garment_shoulder_width'),
('zozotown_page', 'そで丈',  'sleeve_length'),
-- kobo garment measurements
('kobo_garment_measurements', 'chest-width',       'chest_width'),
('kobo_garment_measurements', 'across-shoulder',   'garment_shoulder_width'),
('kobo_garment_measurements', 'sleeve-length',     'sleeve_length'),
('kobo_garment_measurements', 'body-length-back',  'body_length'),
('kobo_garment_measurements', 'waist-width',       'waist_width'),
('kobo_garment_measurements', 'hip-width',         'hip_width'),
('kobo_garment_measurements', 'thigh-width',       'thigh_width'),
('kobo_garment_measurements', 'knee-width',        'knee_width'),
('kobo_garment_measurements', 'leg-opening',       'leg_opening'),
('kobo_garment_measurements', 'inseam',            'garment_inseam'),
('kobo_garment_measurements', 'front-rise',        'front_rise'),
('kobo_garment_measurements', 'back-rise',         'back_rise'),
-- ANSUR II (단위 mm 원본 → 적재 시 cm 변환)
('ansur2', 'stature',                    'height'),
('ansur2', 'chestcircumference',         'chest_girth'),
('ansur2', 'waistcircumference',         'waist_girth'),     -- 배꼽 높이 기준, ISO 허리와 위치 다름
('ansur2', 'buttockcircumference',       'hip_girth'),
('ansur2', 'neckcircumference',          'neck_girth'),
('ansur2', 'biacromialbreadth',          'shoulder_width'),  -- 직선 너비, ISO 는 등 곡면 길이
('ansur2', 'waistbacklength',            'back_length'),
('ansur2', 'sleeveoutseam',              'arm_length'),      -- 어깨 끝~손목 바깥선, 팔길이 정의와 근사
('ansur2', 'bicepscircumferenceflexed',  'upperarm_girth'),  -- 팔 굽힌 상태라 실제보다 큼
('ansur2', 'wristcircumference',         'wrist_girth'),
('ansur2', 'crotchheight',               'inseam'),          -- 샅 높이 ≈ 다리안쪽길이
('ansur2', 'thighcircumference',         'thigh_girth'),
('ansur2', 'calfcircumference',          'calf_girth'),
('ansur2', 'anklecircumference',         'ankle_girth'),
('ansur2', 'chestheight',                'chest_height'),
('ansur2', 'waistheightomphalion',       'waist_height'),    -- 배꼽 높이 기준
('ansur2', 'buttockheight',              'hip_height'),      -- 엉덩이 최대 돌출점 높이 ≈ 엉덩이높이
('ansur2', 'chestbreadth',               'chest_breadth'),
('ansur2', 'chestdepth',                 'chest_depth'),
('ansur2', 'waistbreadth',               'waist_breadth'),
('ansur2', 'waistdepth',                 'waist_depth'),
('ansur2', 'hipbreadth',                 'hip_breadth'),
('ansur2', 'buttockdepth',               'hip_depth'),       -- 엉덩이 두께 ≈ hip_depth
-- BodyM
('bodym', 'height',            'height'),
('bodym', 'chest',             'chest_girth'),
('bodym', 'waist',             'waist_girth'),
('bodym', 'hip',               'hip_girth'),
('bodym', 'arm-length',        'arm_length'),
('bodym', 'leg-length',        'inseam'),                    -- 다리 길이 ≈ 다리안쪽길이
('bodym', 'shoulder-breadth',  'shoulder_width'),            -- 직선 너비
('bodym', 'bicep',             'upperarm_girth'),
('bodym', 'wrist',             'wrist_girth'),
('bodym', 'thigh',             'thigh_girth'),
('bodym', 'calf',              'calf_girth'),
('bodym', 'ankle',             'ankle_girth')
AS new
ON DUPLICATE KEY UPDATE measure_code = new.measure_code;
