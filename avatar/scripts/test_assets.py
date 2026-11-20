# 역할: 기준 신체를 이용한 Blender 생성 검사를 실행하고 결과를 출력합니다.
"""CPU/Blender test. Tests bundled MHR reference, not photograph inference or Azure."""
import json,os,subprocess,sys,tempfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from core.contract import MEASUREMENT_KEYS,prepare_job
from geometry.glb import unpack,body_positions

def main():
    with np.load(ROOT/'models/a_pose.npz',allow_pickle=False) as z:
        vertices=z['vertices']; faces=z['faces']; cid=z['calibration_id']
    outcomes=[]
    with tempfile.TemporaryDirectory() as td:
        surface=Path(td)/'neutral.npz'
        np.savez(surface,vertices=vertices,faces=faces,calibration_id=cid)
        for height in [169,173,180]:
            job=prepare_job({'male':{k:height if k=='height_cm' else None for k in MEASUREMENT_KEYS}})
            job['surface_path']=str(surface)
            with tempfile.TemporaryFile() as out:
                env={**os.environ,'FITME_FD':str(out.fileno()),'SAM_BINDING':str(ROOT/'models/sam_body.npz'),
                     'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'}
                proc=subprocess.run([os.getenv('BLENDER_BIN','blender'),'-b','-Y',str(ROOT/'models/fitme_depth_fixed.blend'),
                    '-t','1','--python-exit-code','1','-P',str(ROOT/'src/geometry/worker.py')],input=json.dumps(job).encode(),
                    pass_fds=(out.fileno(),),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env,timeout=120)
                if proc.returncode:raise RuntimeError(proc.stdout.decode())
                out.seek(0);blob=out.read()
            assert blob[:4]==b'glTF' and int.from_bytes(blob[8:12],'little')==len(blob)
            doc,binary=unpack(blob);p=body_positions(blob)
            assert len(p)==18439 and np.isfinite(p).all()
            assert abs(p[:,2].min())<1e-5
            names={n.get('name') for n in doc['nodes']}
            assert {'fit_shoulder_L','fit_shoulder_R','fit_wrist_L','fit_wrist_R'}<=names
            actual=float(np.ptp(p[:,2])*100)
            assert abs(actual-height)<1, (height,actual)
            assert doc['scenes'][0]['extras']['fitme_measurements']['height_cm']['surface']=='sam'
            outcomes.append({'target_cm':height,'measured_cm':actual,'abs_error_cm':abs(actual-height),'bytes':len(blob)})
        # A stale calibration must fail, not silently bind to the wrong mesh.
        np.savez(surface,vertices=vertices,faces=faces,calibration_id=np.array('wrong-calibration'))
        job['surface_path']=str(surface)
        with tempfile.TemporaryFile() as out:
            env['FITME_FD']=str(out.fileno())
            proc=subprocess.run([os.getenv('BLENDER_BIN','blender'),'-b','-Y',str(ROOT/'models/fitme_depth_fixed.blend'),
                '-t','1','--python-exit-code','1','-P',str(ROOT/'src/geometry/worker.py')],input=json.dumps(job).encode(),
                pass_fds=(out.fileno(),),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env,timeout=120)
            assert proc.returncode!=0 and b'calibration differ' in proc.stdout
    report={'tested':'bundled neutral MHR -> Blender -> GLB on CPU','cases':outcomes,
        'mismatched_calibration_rejected':True,
        'not_tested':['SAM photo inference','GPU Docker build','T4 memory/performance','Azure SQL/ML/Blob'],
        'note':'Only height is remeasured on final MHR skin; other reported measurements are control-mesh measurements.'}
    print(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
