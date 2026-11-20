-- 시드(초안): 신체 ↔ 옷 대응. 단면(옷을 펼친 너비) × 2 ≈ 둘레
INSERT INTO ref.measure_maps (body_measure_code, garment_measure_code, factor) VALUES
('chest_girth',    'chest_width',             2.00),
('waist_girth',    'waist_width',             2.00),
('hip_girth',      'hip_width',               2.00),
('thigh_girth',    'thigh_width',             2.00),
('knee_girth',     'knee_width',              2.00),
('shoulder_width', 'garment_shoulder_width',  1.00),
('arm_length',     'sleeve_length',           1.00),
('inseam',         'garment_inseam',          1.00)
AS new
ON DUPLICATE KEY UPDATE factor = new.factor;
