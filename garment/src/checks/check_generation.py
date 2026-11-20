# 역할: Blender와 기본 의류 템플릿의 GLB 생성 결과를 검사합니다.
"""Exercise real .blend loading/deformation/GLB export without Azure credentials."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
from geometry.mesh_anchors import extract,garment_fitting
from core.garment_specs import DEFAULTS

ROOT=Path(__file__).resolve().parents[1]

def run(job,env=None):
    with os.fdopen(os.memfd_create('fitme-garment-check'),'w+b') as out:
        fd=out.fileno()
        process=subprocess.run([os.getenv('BLENDER_BIN','blender'),'-t','1','-b','-Y',
            '--factory-startup','--python-exit-code','3','-P',str(ROOT/'geometry'/'garment_worker.py')],
            input=json.dumps(job).encode(),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            pass_fds=(fd,),timeout=120,env={**os.environ,'FITME_FD':str(fd),
            'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1',**(env or {})})
        out.seek(0);return process,out.read()


def read_glb(data):
    assert data[:4]==b'glTF' and struct.unpack_from('<II',data,4)==(2,len(data))
    n,chunk=struct.unpack_from('<I4s',data,12);assert chunk==b'JSON'
    doc=json.loads(data[20:20+n]);return doc,data[28+n:]


def accessor(doc,binary,index):
    a=doc['accessors'][index];v=doc['bufferViews'][a['bufferView']]
    count={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
    fmt='<'+{5121:'B',5123:'H',5125:'I',5126:'f'}[a['componentType']]*count
    stride=v.get('byteStride',struct.calcsize(fmt))
    start=v.get('byteOffset',0)+a.get('byteOffset',0)
    return [struct.unpack_from(fmt,binary,start+i*stride) for i in range(a['count'])]


def validate(data,kind):
    doc,binary=read_glb(data)
    triangles=0;vertices=0
    for mesh in doc['meshes']:
        for prim in mesh['primitives']:
            p=accessor(doc,binary,prim['attributes']['POSITION'])
            normal=accessor(doc,binary,prim['attributes']['NORMAL'])
            indices=[x[0] for x in accessor(doc,binary,prim['indices'])]
            assert indices and len(indices)%3==0
            assert all(math.isfinite(v) for point in p+normal for v in point)
            assert all(0<=i<len(p) for i in indices)
            assert all(abs(sum(v*v for v in n)-1)<1e-4 for n in normal)
            triangles+=len(indices)//3;vertices+=len(p)
    parent,anchors,_=extract(data,'garments')
    assert parent=='FitMeGarment'
    fit=garment_fitting(data);assert fit['kind']==kind
    extras=doc['scenes'][doc['scene']]['extras']
    report=extras['fitme_garment_measurements']
    if kind=='slacks':
        assert report=={} and extras['spec']=={}
        assert extras['template_geometry']['deformation_applied'] is False
    assert all(v['abs_error']<1e-5 for v in report.values()),report
    assert triangles==extras['template_geometry']['template_triangles']
    assert not doc.get('extensionsRequired'), 'Export should remain portable'
    return {'bytes':len(data),'export_vertices':vertices,'triangles':triangles,
            'anchors':sorted(anchors),'template_id':fit['template_id'],
            'cage_max_error_cm':max((v['abs_error'] for v in report.values()),default=0.),
            'sha256':hashlib.sha256(data).hexdigest()}


def job_for(kind,spec=None,basis=None):
    return {'garment_id':6 if kind=='crewneck' else 900001,
            'size_id':3 if kind=='crewneck' else 900102,'item_code':'LOCAL-TEST',
            'region':'DEMO','size_label':'M','spec':spec or DEFAULTS[kind],
            'recipe':{'kind':kind,'sleeve_basis':basis or ('shoulder' if kind=='crewneck' else 'none'),
                      'template_id':kind+'_v1'}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path)
    args=parser.parse_args()
    if args.output_dir:args.output_dir.mkdir(parents=True,exist_ok=True)
    cases=[('crewneck_shoulder',job_for('crewneck')),
           ('crewneck_center_back',job_for('crewneck',{**DEFAULTS['crewneck'],'sleeve_length':45},'center_back')),
           ('crewneck_long',job_for('crewneck',{**DEFAULTS['crewneck'],'sleeve_length':60})),
           ('slacks_S',job_for('slacks',{'waist_width':37,'hip_width':47,'front_rise':26,'inseam':72,'thigh_width':29,'knee_width':21,'hem_width':17})),
           ('slacks_M',job_for('slacks')),
           ('slacks_L',job_for('slacks',{'waist_width':43,'hip_width':54,'front_rise':30,'inseam':81,'thigh_width':34,'knee_width':24,'hem_width':20}))]
    results=[]
    for name,job in cases:
        process,data=run(job)
        if process.returncode:raise RuntimeError(process.stdout.decode(errors='replace')[-5000:])
        results.append({'case':name,'status':'PASS',**validate(data,job['recipe']['kind'])})
        if args.output_dir:(args.output_dir/(name+'.glb')).write_bytes(data)
    failures=[('invalid_basis',{**job_for('slacks'),'recipe':{**job_for('slacks')['recipe'],'sleeve_basis':'shoulder'}}),
              ('invalid_template',{**job_for('slacks'),'recipe':{'kind':'slacks','sleeve_basis':'none','template_id':'../slacks'}}),
              ('invalid_kind',{**job_for('slacks'),'recipe':{'kind':'unknown','sleeve_basis':'none','template_id':'slacks_v1'}})]
    rejected=[]
    for name,job in failures:
        process,_=run(job)
        assert process.returncode!=0 and b'FITME_INPUT_ERROR' in process.stdout
        rejected.append(name)
    report={'blender':subprocess.check_output([os.getenv('BLENDER_BIN','blender'),'--version'],text=True).splitlines()[0],
            'cases':results,'rejected_inputs':rejected,
            'scope':'Real template loading and deformation, GLB structure, cage measures; not Azure or physical fit accuracy.'}
    if args.output_dir:(args.output_dir/'cpu_smoke_test.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
