# 역할: 신체 치수 입력 계약과 서버가 정한 고정 자세를 검증합니다.
"""Public ML input and the server-owned Blender pose."""
import math

MEASUREMENT_KEYS = frozenset(('height_cm', 'inseam_cm', 'torso_length_cm', 'shoulder_width_cm', 'arm_length_cm', 'hip_line_height_cm', 'waist_line_height_cm', 'chest_line_height_cm', 'hip_girth_cm', 'hip_width_cm', 'hip_depth_cm', 'belly_girth_cm', 'waist_girth_cm', 'waist_width_cm', 'waist_depth_cm', 'chest_girth_cm', 'chest_width_cm', 'chest_depth_cm', 'ankle_girth_cm', 'calf_girth_cm', 'knee_girth_cm', 'thigh_girth_cm', 'upper_arm_girth_cm', 'wrist_girth_cm', 'back_width_cm', 'underbust_girth_cm', 'belly_front_cm', 'hip_rear_cm', 'rise_arc_cm'))
FIXED_POSE = {
    'reference_pose': 'A',
    'arm_angle_deg': 45,
    'pelvis_tilt_deg': 0,
    'shoulder_tilt_deg': 0,
    'shoulder_slope_deg': 23,
}
SLEEVE_TOLERANCE_DEG = 1
PREDICTION_KEYS = MEASUREMENT_KEYS - {'height_cm'}


def validate_prediction(payload):
    if not isinstance(payload, dict) or set(payload) != {'male'}:
        raise ValueError('Expected male containing exactly 28 predicted measurements')
    values = payload['male']
    if not isinstance(values, dict) or set(values) != PREDICTION_KEYS:
        raise ValueError('Expected all 28 measurements without height_cm')
    for value in values.values():
        if type(value) not in (float, int) or not math.isfinite(value) or not 0 < value < 1000:
            raise ValueError('All 28 predictions must be positive finite cm values')
    return {'male': dict(values)}


def prepare_prediction(payload, height_cm):
    values = validate_prediction(payload)['male']
    return prepare_job({'male': {**values, 'height_cm': height_cm}})
def prepare_job(payload):
    if not isinstance(payload, dict) or set(payload) != {'male'}:
        raise ValueError('Expected an object with the single key male')
    values = payload['male']
    if not isinstance(values, dict):
        raise ValueError('male must be an object')
    missing = sorted(MEASUREMENT_KEYS - values.keys())
    unknown = sorted(values.keys() - MEASUREMENT_KEYS)
    if missing or unknown:
        raise ValueError(f'Missing fields: {missing}. Unexpected fields: {unknown}')
    if values['height_cm'] is None:
        raise ValueError('height_cm is required')
    for name, value in values.items():
        if value is None:
            continue
        if type(value) not in (float, int) or not 0 < value < 1000 or not math.isfinite(value):
            raise ValueError(f'{name} must be a positive finite number below 1000 cm')
    return {'male': {**values, **FIXED_POSE}}
