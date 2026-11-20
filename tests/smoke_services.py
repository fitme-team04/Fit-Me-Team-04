# 역할: 실제 API import·요청 계약·템플릿 경로와 Compose 시작 조건을 검사합니다.
from pathlib import Path
import os
import subprocess
import sys
import yaml

base=Path(__file__).resolve().parents[1]
scripts={
'avatar': '''
import asyncio, os
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from api import avatar
from core.contract import MEASUREMENT_KEYS
from core.features import make_features, SAM_MEASUREMENT_KEYS
payload={'male':{key:175 if key=='height_cm' else 40 for key in MEASUREMENT_KEYS}}
features=make_features({key: payload['male'][key] for key in (*SAM_MEASUREMENT_KEYS, 'height_cm')},175,70)
del payload['male']['height_cm']
def handler(request):
    import json
    assert json.loads(request.content)==features
    return httpx.Response(200,json=payload)
original=httpx.AsyncClient
def client(**kwargs):return original(transport=httpx.MockTransport(handler),**kwargs)
with patch.dict(os.environ,{'AZURE_ML_ENDPOINT':'https://fitme-test.koreacentral.inference.ml.azure.com/score','AZURE_ML_KEY':'test-only','AZURE_ML_AUTH':'key'}),patch.object(avatar.httpx,'AsyncClient',side_effect=client):
    result=asyncio.run(avatar.predict(features))
    assert result['male']['reference_pose']=='A'
assert TestClient(avatar.app).get('/health').status_code==200
print('PASS: avatar API import, health and direct JSON ML response')
''',
'garment': '''
from unittest.mock import patch
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from api import garments
from core.garment_specs import DEFAULTS
from geometry.template_catalog import DEFAULT_ROOT
assert DEFAULT_ROOT.is_dir()
spec=DEFAULTS['crewneck']
rows=[{'garment_id':1,'item_code':'real-test','category':'상의','source_name':'test-source','region':'KR','size_label':'M','measure_code':k,'value_cm':v} for k,v in spec.items()]
aliases=[{'alias_name':'sleeve-length'}]
with patch.object(garments,'query',side_effect=[rows,aliases]),patch.object(garments,'render',return_value=JSONResponse({'status':'ready'})):
    response=TestClient(garments.app).post('/api/garments',json={'item_code':'real-test','size_id':2},headers={'X-FitMe-Subject':'test-only'})
    assert response.status_code==200,response.text
assert TestClient(garments.app).get('/demo').status_code==200
print('PASS: garment API import, real template lookup, validated generation route and demo')
'''
}
for service,code in scripts.items():
    src=base/service/'src'
    env={**os.environ,'PYTHONPATH':str(src),'PYTHONDONTWRITEBYTECODE':'1'}
    result=subprocess.run([sys.executable,'-B','-c',code],cwd=src,env=env,capture_output=True,text=True)
    print(result.stdout)
    if result.returncode:
        print(result.stderr)
        raise SystemExit(result.returncode)
    config=yaml.safe_load((base/service/'compose.yaml').read_text(encoding='utf-8'))
    assert service in config['services']
    if service=='avatar':
        assert config['services']['avatar']['depends_on']['model-sync']['condition']=='service_completed_successfully'
print('PASS: both Compose definitions parse; model-sync gates avatar startup')
