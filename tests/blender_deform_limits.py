# 역할: 샅앞뒤길이·너비·기준 높이가 범위를 벗어나도 유한한 GLB가 생성되는지 검사합니다.
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

import numpy as np

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'avatar/src'))
from core.test_prediction import example_prediction
from core.contract import FIXED_POSE
from geometry import worker
from geometry.deform import solve
from geometry.glb import unpack,body_positions


with tempfile.TemporaryDirectory(dir=BASE/'avatar/.cache') as folder:
    for target in (1.,999.):
        job=example_prediction(180.)
        job['male']['rise_arc_cm']=target
        output=Path(folder)/'body.glb'
        os.environ['FITME_FD']=str(os.open(output,os.O_CREAT|os.O_TRUNC|os.O_RDWR,0o600))
        with patch.object(sys,'stdin',io.StringIO(json.dumps(job))):
            worker.main()
        blob=output.read_bytes()
        doc,_=unpack(blob)
        extras=doc['scenes'][0]['extras']
        assert np.isfinite(body_positions(blob)).all()
        assert 'rise_arc_cm' in extras['fitme_adjustments']
        report=extras['fitme_measurements']['rise_arc_cm']
        assert report['target']==target
        assert report['applied_target']!=target
        print('PASS: out-of-range rise clamped with GLB audit metadata')
    fitted,_,_,_,_,applied=solve('male',{'male':dict(FIXED_POSE,height_cm=180.,hip_width_cm=100.,hip_girth_cm=40.)})
    assert np.isfinite(fitted).all()
    assert 0<applied['hip_width_cm']<100.
    print('PASS: width/girth conflict clamped')
    job=example_prediction(180.)
    job['male'].update(inseam_cm=120.,hip_line_height_cm=80.,waist_line_height_cm=70.,chest_line_height_cm=60.)
    fitted,_,_,_,_,applied=solve('male',job)
    assert np.isfinite(fitted).all()
    heights=[0,applied['inseam_cm'],applied['hip_line_height_cm'],applied['waist_line_height_cm'],
             applied['chest_line_height_cm'],applied['waist_line_height_cm']+applied['torso_length_cm'],180.]
    assert min(np.diff(heights))>=1.5-1e-7
    print('PASS: overlapping landmarks corrected while preserving height')
