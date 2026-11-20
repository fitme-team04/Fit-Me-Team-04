# 역할: 기준 영역을 SAM에 대응시킨 뒤 실제 SAM 단면에서 ML 입력용 치수 11개를 계산합니다.
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import numpy as np
from mathutils.bvhtree import BVHTree
from geometry.bind_sam import digest
from geometry.deform import solve
from geometry.sam_dimensions import measure_dimensions
from core.contract import FIXED_POSE
from core.features import SAM_MEASUREMENT_KEYS
from core.features import positive, clean_measurements


def load_surface(surface_path,body=None):
    """Return actual SAM topology and projected guides; never deform the SAM body."""
    body=bpy.data.objects['GEO-body_male_realistic'] if body is None else body
    mesh = body.data
    base = np.array([v.co[:] for v in mesh.shape_keys.reference_key.data])
    posed, tri, rings, ids, arc, _ = solve('male', {'male': dict(FIXED_POSE)},body=body)
    with np.load(os.getenv('SAM_BINDING', '/models/sam_body.npz'), allow_pickle=False) as binding:
        if (int(binding['schema_version']) != 2 or str(binding['ref_hash']) != digest(base, tri)
                or str(binding['fixed_pose_json']) != json.dumps(FIXED_POSE, sort_keys=True)):
            raise ValueError('Incompatible SAM calibration')
        reference = binding['control_reference']
        if reference.shape != posed.shape or not np.allclose(reference, posed, atol=1e-5):
            raise ValueError('Control reference pose differs')
        neutral = binding['vertices']
        faces = binding['faces']
        with np.load(surface_path, allow_pickle=False) as surface:
            if (str(surface['calibration_id']) != str(binding['calibration_id'])
                    or surface['vertices'].shape != binding['neutral'].shape
                    or not np.array_equal(surface['faces'], binding['sam_faces'])):
                raise ValueError('Incompatible SAM surface')
            actual = neutral + (surface['vertices'] - binding['neutral']) @ binding['linear']
    if not np.isfinite(actual).all():
        raise ValueError('Non-finite SAM surface')
    tree = BVHTree.FromPolygons(neutral.tolist(), faces.tolist(), all_triangles=True)
    projected = np.empty_like(reference)
    distances = []
    for index, point in enumerate(reference):
        nearest, _, face_index, distance = tree.find_nearest(point)
        if nearest is None:
            raise ValueError('SAM landmark projection failed')
        triangle = faces[face_index]
        a, b, c = neutral[triangle]
        uv = np.linalg.lstsq(np.column_stack((b-a, c-a)), np.asarray(nearest)-a, rcond=None)[0]
        weights = np.array([1-uv.sum(), uv[0], uv[1]])
        if not np.isfinite(weights).all():
            raise ValueError('Invalid surface landmark weights')
        # BVH는 float32 좌표를 반환하므로 가느다란 삼각형 경계의 오차를 표면 안으로 제한합니다.
        weights = np.clip(weights, 0, 1)
        weights /= weights.sum()
        projected[index] = weights @ actual[triangle]
        distances.append(distance)
    if np.percentile(distances, 95) > .08 or max(distances) > .20:
        raise ValueError('SAM reference surface is too far from measurement landmarks')
    return actual, faces, projected, rings, ids, arc


def measure(surface_path,body=None):
    actual, faces, projected, rings, _, arc = load_surface(surface_path,body)
    measures = measure_dimensions(actual, faces, projected, rings, arc)
    height = positive(measures['height_cm'])
    return {'height_cm': height, **clean_measurements(measures, height)}



if __name__ == '__main__':
    job = json.load(sys.stdin)
    print('FITME_SAM_MEASUREMENTS ' + json.dumps(measure(job['surface_path']), allow_nan=False), flush=True)
