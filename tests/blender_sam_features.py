# 역할: 기준 SAM 표면의 치수 11개와 모델 크기 변화에 대한 cm 정규화 불변성을 검사합니다.
# 실행 시 기준 blend를 열고 SciPy가 설치된 Blender Python을 사용합니다.
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE/'avatar/src'))
from geometry.sam_measure_worker import measure
from core.features import make_features, SAM_MEASUREMENT_KEYS
from geometry import sam_dimensions

with np.load(os.environ['SAM_BINDING'], allow_pickle=False) as binding:
    neutral = binding['neutral'].copy()
    faces = binding['sam_faces'].copy()
    calibration_id = binding['calibration_id'].copy()

with tempfile.TemporaryDirectory(dir=BASE/'avatar/.cache') as folder:
    ratios = []
    for scale in (1., 1.25):
        path = Path(folder)/'synthetic-surface.npz'
        np.savez(path, vertices=neutral*scale, faces=faces, calibration_id=calibration_id)
        measured = measure(path)
        features = make_features(measured, 175., 70.)
        ratios.append([features['sam_measurements'][key] for key in SAM_MEASUREMENT_KEYS])
        if scale == 1.:
            initial_height = measured['height_cm']
        else:
            np.testing.assert_allclose(measured['height_cm']/initial_height, scale, rtol=1e-5)
    # 단면이 정점을 스칠 때의 부동소수점 차이에 대해 0.1 mm를 허용합니다.
    np.testing.assert_allclose(ratios[0], ratios[1], rtol=1e-5, atol=.01)
    original_sections = sam_dimensions.sections

    def missing_one_arm(vertices, triangles, origin, normal):
        if origin[0] > 0 and abs(normal[0]) > .1 and abs(normal[2]) > .1:
            return []
        return original_sections(vertices, triangles, origin, normal)

    with patch.object(sam_dimensions, 'sections', side_effect=missing_one_arm):
        partial = measure(path)
    assert partial['wrist_girth_cm'] is None
    assert partial['upper_arm_girth_cm'] is None
    assert partial['calf_girth_cm'] > 0
    assert partial['hip_girth_cm'] > 0

    def missing_crotch(vertices, triangles, origin, normal):
        if np.array_equal(normal, [1., 0., 0.]):
            return []
        return original_sections(vertices, triangles, origin, normal)

    with patch.object(sam_dimensions, 'sections', side_effect=missing_crotch):
        partial = measure(path)
    for key in ('inseam_cm', 'hip_girth_cm', 'hip_width_cm', 'hip_depth_cm', 'hip_line_height_cm', 'thigh_girth_cm'):
        assert partial[key] is None, key
    assert partial['calf_girth_cm'] > 0
    assert partial['wrist_girth_cm'] > 0
    with patch.object(sam_dimensions, 'sections', return_value=[]):
        missing = make_features(measure(path), 175., 70.)
    assert all(value is None for value in missing['sam_measurements'].values())
print('PASS: 11 SAM surface measurements; all 11 normalized cm values invariant under 1.25x surface scaling')
print('PASS: one-arm, crotch and all-section failures yield local nulls without template fallback')
