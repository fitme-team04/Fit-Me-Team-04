# 역할: SAM 표면·바인딩 없이 Blob 기본 모델을 변형하고 입력 키·앵커·치수 보고서를 검증합니다.
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE/'avatar/src'))
from core.contract import MEASUREMENT_KEYS, FIXED_POSE, prepare_job
from geometry.deform import solve
from geometry.glb import body_positions
from geometry.mesh_anchors import extract
from geometry import worker

_, _, _, _, _, defaults = solve('male', {'male': dict(FIXED_POSE)})
baseline = {key: float(defaults[key]) for key in MEASUREMENT_KEYS}
os.environ['SAM_BINDING'] = '/nonexistent-binding-not-required-for-output.npz'
heights=[]
with tempfile.TemporaryDirectory(dir=BASE/'avatar/.cache') as folder:
    for scale in (1., 1.05):
        values = dict(baseline, height_cm=baseline['height_cm']*scale)
        job = prepare_job({'male': values})
        path = Path(folder)/'base-body.glb'
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_TRUNC, 0o600)
        os.environ['FITME_FD'] = str(fd)
        with patch.object(sys, 'stdin', io.StringIO(json.dumps(job))):
            worker.main()
        blob=path.read_bytes()
        parent, anchors, report=extract(blob, 'avatars')
        height=float(np.ptp(body_positions(blob)[:, 2])*100)
        heights.append(height)
        np.testing.assert_allclose(height, values['height_cm'], atol=.6)
        assert all(value['surface']=='template' for value in report.values())
        assert set(MEASUREMENT_KEYS) <= report.keys()
        assert len(anchors)==6
    assert heights[1]>heights[0]+baseline['height_cm']*.04
print('PASS: base-template GLB changes height; all required anchors and measurement reports; no SAM output mesh dependency')
