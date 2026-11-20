-- 시드(초안): 치수 항목 정의. ISO 8559-1 조항은 clad-body 기준, 모르면 NULL
INSERT INTO ref.measure_definitions (measure_code, korean_name, body_part, measure_type, basis, iso_clause) VALUES
-- 신체 (basis = body)
('height',          '키',            'full',  'height',  'body', '5.1.1'),
('chest_girth',     '가슴둘레',      'torso', 'girth',   'body', '5.3.4'),
('waist_girth',     '허리둘레',      'torso', 'girth',   'body', '5.3.10'),
('stomach_girth',   '배둘레',        'torso', 'girth',   'body', NULL),
('hip_girth',       '엉덩이둘레',    'torso', 'girth',   'body', '5.3.13'),
('neck_girth',      '목둘레',        'neck',  'girth',   'body', '5.3.2'),
('shoulder_width',  '어깨너비',      'torso', 'length',  'body', '5.4.2'),   -- ISO 는 등 쪽 곡면 길이
('back_length',     '등길이',        'torso', 'length',  'body', '5.4.5'),
('arm_length',      '팔길이',        'arm',   'length',  'body', NULL),
('upperarm_girth',  '위팔둘레',      'arm',   'girth',   'body', '5.3.16'),
('wrist_girth',     '손목둘레',      'arm',   'girth',   'body', '5.3.19'),
('inseam',          '다리안쪽길이',  'leg',   'height',  'body', '5.1.15'),  -- ISO 는 바닥~샅 높이
('thigh_girth',     '허벅지둘레',  'leg',   'girth',   'body', '5.3.20'),
('knee_girth',      '무릎둘레',      'leg',   'girth',   'body', '5.3.22'),
('calf_girth',      '종아리둘레',    'leg',   'girth',   'body', '5.3.24'),
('ankle_girth',     '발목둘레',      'leg',   'girth',   'body', NULL),
('chest_height',    '가슴높이',      'torso', 'height',  'body', NULL),
('waist_height',    '허리높이',      'torso', 'height',  'body', NULL),
('hip_height',      '엉덩이높이',    'torso', 'height',  'body', NULL),
('chest_breadth',   '가슴너비',      'torso', 'breadth', 'body', NULL),
('chest_depth',     '가슴두께',      'torso', 'depth',   'body', NULL),
('waist_breadth',   '허리너비',      'torso', 'breadth', 'body', NULL),
('waist_depth',     '허리두께',      'torso', 'depth',   'body', NULL),
('hip_breadth',     '엉덩이너비',    'torso', 'breadth', 'body', NULL),
('hip_depth',       '엉덩이두께',    'torso', 'depth',   'body', NULL),
-- 옷 실측 (basis = garment)
('body_length',             '총장',          'torso', 'length',  'garment', NULL),
('chest_width',             '가슴단면',      'torso', 'breadth', 'garment', NULL),
('garment_shoulder_width',  '어깨너비(옷)',  'torso', 'breadth', 'garment', NULL),
('sleeve_length',           '소매길이',      'arm',   'length',  'garment', NULL),
('waist_width',             '허리단면',      'torso', 'breadth', 'garment', NULL),
('hip_width',               '엉덩이단면',    'torso', 'breadth', 'garment', NULL),
('thigh_width',             '허벅지단면',    'leg',   'breadth', 'garment', NULL),
('knee_width',              '무릎단면',      'leg',   'breadth', 'garment', NULL),
('leg_opening',             '밑단단면',      'leg',   'breadth', 'garment', NULL),
('garment_inseam',          '안쪽기장',      'leg',   'length',  'garment', NULL),
('front_rise',              '앞밑위',        'torso', 'length',  'garment', NULL),
('back_rise',               '뒷밑위',        'torso', 'length',  'garment', NULL)
AS new
ON DUPLICATE KEY UPDATE
  korean_name = new.korean_name, body_part = new.body_part, measure_type = new.measure_type,
  basis = new.basis, iso_clause = new.iso_clause;
