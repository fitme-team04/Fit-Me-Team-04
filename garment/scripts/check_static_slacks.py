# 역할: 하의가 입력 치수 없이도 출력되고 다른 치수를 보내도 원본 정점·기준점이 유지되는지 검증합니다.
import bpy
import io
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from geometry import garment_worker
from geometry.template_binding import geometry,digest
from geometry.glb import unpack
from geometry.mesh_anchors import extract

release=ROOT/'releases/final-garments'
models=release/'models'
entry=json.loads((models/'registry.json').read_text())['templates']['black_midrise_straight_v1']
with bpy.data.libraries.load(str(models/entry['blend']),link=False) as (src,dst):dst.objects=[entry['object']]
obj=dst.objects[0];bpy.context.collection.objects.link(obj)
v,f=geometry(obj);original=digest(v,f)
os.environ['GARMENT_TEMPLATE_DIR']=str(models)
out=release/'pants/static-validation';out.mkdir(exist_ok=True)
reports=[]
reference_anchors=None
for name,spec in [('missing',None),('small',{'waist_width':28,'inseam':45}),('large',{'waist_width':999,'hip_width':999,'inseam':999})]:
    job={'recipe':{'kind':'slacks','template_id':'black_midrise_straight_v1','sleeve_basis':'none'},'size_label':name}
    if spec is not None:job['spec']=spec
    os.environ['FITME_FD']=str(os.open(out/(name+'.glb'),os.O_CREAT|os.O_TRUNC|os.O_RDWR,0o600))
    with patch.object(sys,'stdin',io.StringIO(json.dumps(job))):garment_worker.main()
    current=next(obj for obj in bpy.context.scene.objects if obj.type=='MESH')
    actual,faces=geometry(current)
    assert np.array_equal(v,actual) and np.array_equal(f,faces)
    doc,_=unpack((out/(name+'.glb')).read_bytes())
    extras=doc['scenes'][doc.get('scene',0)]['extras']
    assert extras['spec']=={} and extras['fitme_garment_measurements']=={}
    assert extras['template_geometry']['deformation_applied'] is False
    assert extras['template_geometry']['source_geometry_sha256']==original
    _,exported_anchors,_=extract((out/(name+'.glb')).read_bytes(),'garments')
    assert set(exported_anchors)=={'fit_anchor_waist','fit_crotch','fit_hem_L','fit_hem_R'}
    if reference_anchors is None:reference_anchors=exported_anchors
    else:assert exported_anchors==reference_anchors
    waist=next(obj for obj in bpy.context.scene.objects if obj.name=='fit_anchor_waist')
    assert np.allclose(waist.location,[0,0,0])
    reports.append({'case':name,'unchanged_geometry':True,'source_geometry_sha256':original,'fixed_waist_anchor':True})
(out/'report.json').write_text(json.dumps(reports,indent=2)+'\n')
print('PASS: three worker GLBs preserve exact source vertices, topology and waist anchor')
