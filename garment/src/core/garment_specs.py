# 역할: 의류 종류별 필수 실측 코드·범위·측정 기준을 검증합니다.
"""Shared API/Blender validation. All product measures are in centimetres."""
import math

LIMITS = {
    'crewneck': {'body_length': (45,100), 'garment_shoulder_width': (30,70),
                'chest_width': (35,85), 'sleeve_length': (10,100)},
    'slacks': {'waist_width': (28,65), 'hip_width': (36,75),
               'inseam': (45,100), 'thigh_width': (20,45)},
}
DEFAULTS = {'crewneck': {'body_length':69, 'garment_shoulder_width':46.5,
                        'chest_width':53, 'sleeve_length':22},
            'slacks': {'waist_width':40, 'hip_width':50, 'inseam':76, 'thigh_width':31}}
SLACKS_REFERENCE = {'waist_width':40, 'hip_width':50, 'front_rise':28,
                    'inseam':76, 'thigh_width':31, 'knee_width':22, 'hem_width':18}


def validate_spec(kind, spec, sleeve_basis):
    if kind not in LIMITS:
        raise ValueError('Unsupported garment kind: '+str(kind))
    expected = {'shoulder','center_back'} if kind == 'crewneck' else {'none'}
    if sleeve_basis not in expected:
        raise ValueError('Invalid sleeve_basis for '+kind)
    missing = set(LIMITS[kind]) - spec.keys()
    if missing:
        raise ValueError('Missing garment measurements: '+', '.join(sorted(missing)))
    for key,(low,high) in LIMITS[kind].items():
        v = spec[key]
        if type(v) not in (float,int) or not math.isfinite(v) or not low <= v <= high:
            raise ValueError(f'{key} must be between {low} and {high} cm')
    if kind == 'slacks':
        if not spec['hip_width'] >= spec['waist_width']:
            raise ValueError('hip_width must be at least waist_width')
        if spec['hip_width'] < spec['thigh_width'] * 1.35:
            raise ValueError('Hip and thigh measurements are incompatible with this cage')
    return {key:float(spec[key]) for key in LIMITS[kind]}


def complete_slacks_spec(spec, reference=None):
    # 역할: 상품에 없는 앞밑위·무릎·밑단 입력 대신 등록 원형의 연결 부위 비율로 내부 케이지를 구성합니다.
    reference = SLACKS_REFERENCE if reference is None else reference
    fallback = SLACKS_REFERENCE
    rise_ratio = reference['front_rise']/reference['hip_width'] if 'front_rise' in reference else fallback['front_rise']/fallback['hip_width']
    knee_ratio = reference['knee_width']/reference['thigh_width'] if 'knee_width' in reference else fallback['knee_width']/fallback['thigh_width']
    hem_ratio = reference['hem_width']/reference['thigh_width'] if 'hem_width' in reference else fallback['hem_width']/fallback['thigh_width']
    return {**spec,
            'front_rise': spec['hip_width'] * rise_ratio,
            'knee_width': spec['thigh_width'] * knee_ratio,
            'hem_width': spec['thigh_width'] * hem_ratio}
