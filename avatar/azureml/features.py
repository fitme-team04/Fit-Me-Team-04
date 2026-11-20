# 역할: 실제 키에 맞춘 SAM 측정값 11개와 키·몸무게의 ML JSON 계약을 정의합니다.
import math

SCHEMA_VERSION = 2
METHOD = 'sam_surface_sections_11_v2'
SAM_MEASUREMENT_KEYS = (
    'inseam_cm', 'hip_girth_cm', 'hip_width_cm', 'hip_depth_cm', 'hip_line_height_cm',
    'ankle_girth_cm', 'calf_girth_cm', 'knee_girth_cm', 'thigh_girth_cm',
    'upper_arm_girth_cm', 'wrist_girth_cm',
)
INPUT_COLUMNS = ('height_cm', 'weight_kg') + SAM_MEASUREMENT_KEYS


def positive(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError('Expected a positive finite number')
    return float(value)


def measurement_or_none(value):
    # Missing or unusable SAM values are JSON null, never a template fallback.
    try:
        value = positive(value)
    except ValueError:
        return None
    return value if value < 1000 else None


def clean_measurements(values, height_cm):
    result = {key: measurement_or_none(values[key]) for key in SAM_MEASUREMENT_KEYS}
    for key in ('inseam_cm', 'hip_width_cm', 'hip_depth_cm', 'hip_line_height_cm'):
        if result[key] is not None and result[key] >= height_cm:
            result[key] = None
    return result


def make_features(measures, height_cm, weight_kg):
    if not isinstance(measures, dict) or set(measures) != set(SAM_MEASUREMENT_KEYS) | {'height_cm'}:
        raise ValueError('Expected SAM height and exactly 11 measured cm values')
    height_cm = positive(height_cm)
    scale = height_cm / positive(measures['height_cm'])
    return validate_features({
        'schema_version': SCHEMA_VERSION, 'measurement_method': METHOD,
        'height_cm': height_cm, 'weight_kg': positive(weight_kg),
        'sam_measurements': {key: None if measurement_or_none(measures[key]) is None
                             else measurement_or_none(measures[key]) * scale
                             for key in SAM_MEASUREMENT_KEYS},
    })


def validate_features(value):
    if not isinstance(value, dict) or set(value) != {
        'schema_version', 'measurement_method', 'height_cm', 'weight_kg', 'sam_measurements'
    }:
        raise ValueError('Invalid feature record')
    if type(value['schema_version']) is not int or value['schema_version'] != SCHEMA_VERSION or value['measurement_method'] != METHOD:
        raise ValueError('Unsupported measurement contract')
    if not isinstance(value['sam_measurements'], dict) or set(value['sam_measurements']) != set(SAM_MEASUREMENT_KEYS):
        raise ValueError('Expected exactly 11 SAM measurements')
    return dict(value, height_cm=positive(value['height_cm']), weight_kg=positive(value['weight_kg']),
                sam_measurements=clean_measurements(value['sam_measurements'], positive(value['height_cm'])))
