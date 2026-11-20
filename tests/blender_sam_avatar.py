"""Run with the guide .blend open and SAM_BINDING set; no photo/GPU/Blob needed."""
import os
from pathlib import Path
import sys
import tempfile

import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'avatar/src'))
from geometry.sam_avatar_worker import build_avatar
from geometry.sam_measure_worker import load_surface
from geometry.glb import unpack, body_positions
from geometry.mesh_anchors import extract

with np.load(os.environ['SAM_BINDING'],allow_pickle=False) as binding:
    neutral = binding['neutral'].copy()
    faces = binding['sam_faces'].copy()
    calibration = binding['calibration_id'].copy()

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder)/'surface.npz'
    np.savez(path,vertices=neutral,faces=faces,calibration_id=calibration)
    original, original_faces, *_ = load_surface(path)
    data = build_avatar(path,170.)
    exported = body_positions(data)
    expected = original.copy()
    expected[:,2] -= expected[:,2].min()
    expected *= 1.7/np.ptp(original[:,2])
    np.testing.assert_allclose(exported,expected,rtol=1e-6,atol=1e-6)
    doc,binary = unpack(data)
    primitive = doc['meshes'][0]['primitives'][0]
    accessor = doc['accessors'][primitive['indices']]
    view = doc['bufferViews'][accessor['bufferView']]
    triangles = np.frombuffer(binary,'<u4',count=accessor['count'],offset=view['byteOffset']).reshape(-1,3)
    np.testing.assert_array_equal(triangles,original_faces)
    _, anchors, report = extract(data,'avatars')
    assert len(anchors) == 8 and {'fit_neck_L','fit_neck_R'} <= anchors.keys()
    assert abs(report['height_cm']['measured']-170.) < .001
    assert doc['scenes'][0]['extras']['body_geometry_source'] == 'sam_surface'
print('PASS: original SAM vertices/topology, uniform height, anchors and report')
