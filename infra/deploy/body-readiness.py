# 역할: 신체 VM의 실제 배포 준비 상태를 비밀 출력 없이 JSON 보고서로 저장합니다.
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

root=Path('/opt/fitme-avatar')
manifest=json.loads((root/'models/bundled_assets.json').read_text())['files']
originals={}
for name in ('mhr_model.pt','fitme_depth_fixed.blend','a_pose.npz','sam_body.npz'):
    path=root/'models'/name
    matched=False
    if path.is_file() and path.stat().st_size==manifest[name]['bytes']:
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(8*1024*1024),b''): digest.update(block)
        matched=digest.hexdigest()==manifest[name]['sha256']
    originals[name]=matched
checkpoints=('sam/model.ckpt','sam/model_config.yaml','vitdet/model_final_f05665.pkl','moge/model.pt')
missing=[name for name in checkpoints if not (root/'models'/name).is_file()]
try:
    result=subprocess.run(['docker','info','--format','{{json .Runtimes}}'],capture_output=True,text=True,timeout=10)
    docker_runtime='nvidia' in json.loads(result.stdout) if result.returncode==0 else False
except Exception:
    docker_runtime=False
env={}
for line in (root/'.env').read_text().splitlines():
    if '=' in line and not line.lstrip().startswith('#'):
        key,value=line.split('=',1);env[key.strip()]=value.strip()
import sys
sys.path.insert(0,str(root/'src'))
from core.ml_endpoint import endpoint_settings
from core.test_prediction import prediction_mode
try:
    mode=prediction_mode(env)
    ml_ready=False
    if mode == 'azure_ml':
        endpoint_settings(env)
        ml_ready=True
    prediction_ready=True
except ValueError:
    ml_ready=False
    prediction_ready=False
    mode="invalid"
try:
    with urllib.request.urlopen('http://10.4.2.4:8001/health',timeout=3) as response:
        api_up=response.status==200 and json.load(response).get('status')=='ok'
except Exception:
    api_up=False
report={'source_ready':(root/'src/api/avatar.py').is_file(),
        'original_assets_verified':originals,'missing_sam_checkpoints':missing,
        'nvidia_container_runtime_configured':docker_runtime,'ml_endpoint_configured':ml_ready, 'ml_endpoint_inference_verified':False,
        'prediction_mode':mode,'prediction_ready':prediction_ready,
        'body_api_running':api_up,'photo_test':'not_run_no_photo',
        'body_geometry_source':'sam_surface', 'ml_required_for_avatar':False,
        'ready_to_start':all(originals.values()) and not missing and docker_runtime}
(root/'deployment/readiness.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
