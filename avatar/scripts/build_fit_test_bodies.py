# 역할: 실제 신체 변형기로 29개 치수별 ±5% 및 복합 체형을 생성하고 재현 가능한 테스트 입력을 저장합니다.
import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[2]/'avatar'
sys.path.insert(0, str(ROOT/'src'))
from core.contract import FIXED_POSE, MEASUREMENT_KEYS, prepare_job
from geometry.deform import solve, points
from geometry.measure import analyze
from geometry.glb import export


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    _,_,_,_,_,defaults=solve('male',{'male':dict(FIXED_POSE)})
    baseline={key:float(defaults[key]) for key in MEASUREMENT_KEYS};baseline['height_cm']=175.
    cases=[('baseline',dict(baseline),{})]
    for key in sorted(baseline):
        for factor in (.95,1.05):
            values=dict(baseline);values[key]*=factor
            cases.append((key+('_minus5' if factor<1 else '_plus5'),values,{key:factor}))
    for factor in (.95,1.05):
        cases.append(('joint_'+str(factor),{key:value*factor for key,value in baseline.items()},dict.fromkeys(baseline,factor)))
    report={'synthetic':True,'not_ml_predictions':True,'baseline':baseline,'cases':[]}
    for name,values,changed in cases:
        start=time.monotonic()
        try:
            job=prepare_job({'male':values})
            vertices,faces,rings,ids,arc,applied=solve('male',job)
            vertices[:,2]-=vertices[:,2].min()
            actual,anchors=analyze(vertices,rings,ids,arc)
            for side,label in ((-1,'R'),(1,'L')):
                wrist=next(loop for tag,s,loop in rings if tag=='wrist' and s==side)
                for tag,position in [('shoulder',vertices[ids['tip',side]]),('wrist',points(vertices,wrist).mean(0))]:
                    anchors.append({'name':'fit_'+tag+'_'+label,'translation':[float(position[0]),float(position[2]),float(-position[1])]})
            np.savez_compressed(output/(name+'.npz'),vertices=vertices,faces=faces)
            (output/(name+'.anchors.json')).write_text(json.dumps(anchors)+'\n')
            if name=='baseline' or name.startswith('joint'):
                (output/(name+'.glb')).write_bytes(export([('FitMe_Body',vertices,faces)],anchors))
            result={'name':name,'ok':True,'changed':changed,'requested':values,
                    'applied':{k:float(applied[k]) for k in baseline},'actual':{k:float(actual[k]) for k in baseline}}
        except Exception as exc:
            result={'name':name,'ok':False,'changed':changed,'error':str(exc)}
        result['seconds']=round(time.monotonic()-start,2)
        report['cases'].append(result)
        (output/'body-test-inputs.json').write_text(json.dumps(report,indent=2)+'\n')
        print('FITME_BODY_CASE '+json.dumps({k:result[k] for k in ('name','ok','seconds')}),flush=True)


if __name__=='__main__':main()
