#!/usr/bin/env bash
# 역할: 웹 VM의 3D 연결 설정·서비스·경로를 비밀 출력 없이 점검합니다.
set -euo pipefail
cd /opt/fitme-web
python3 - <<'PY'
import json
from pathlib import Path
import socket
import subprocess
import urllib.request

keys = ('BODY_MODEL_VM_URL', 'GARMENT_MODEL_VM_URL', 'BODY_MODEL_BLOB_BASE', 'GARMENT_MODEL_BLOB_BASE')
result = subprocess.run(['docker', 'compose', 'config', '--format', 'json'], capture_output=True, text=True)
if result.returncode:
    raise SystemExit('Compose configuration inspection failed; details suppressed')
config = json.loads(result.stdout)
for name, service in config['services'].items():
    env = service.get('environment', {})
    print(json.dumps({'service': name, '3d_settings_present': {key: bool(env.get(key)) for key in keys}}, sort_keys=True))
print('app.env exists:', Path('app.env').is_file())
print('app service exists:', 'app' in config['services'])
for path in ('/api/health', '/openapi.json', '/api/v2/model-pair/status'):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8766'+path, timeout=20) as response:
            data = json.load(response)
            if path == '/openapi.json':
                print('Web 3D route present:', '/api/v2/model-pair' in data.get('paths', {}))
            elif path.endswith('/status'):
                print('Web 3D configured:', data.get('configured'), 'authenticated:', data.get('authenticated'))
            else:
                print('Web health HTTP:', response.status, 'version:', data.get('version'))
    except Exception:
        print('CHECK FAILED:', path)
for label, host, port in [('body', '10.4.2.4', 8001), ('garment', '10.4.2.5', 8002)]:
    try:
        with socket.create_connection((host, port), timeout=3):
            print('API TCP reachable:', label)
    except OSError:
        print('API TCP not reachable:', label)
PY
