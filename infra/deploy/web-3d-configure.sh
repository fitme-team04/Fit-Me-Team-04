#!/usr/bin/env bash
# 역할: 웹 VM의 3D 연결 주소 네 개만 적용하고 기존 이미지로 웹 앱을 재시작·검증합니다.
set -euo pipefail
cd /opt/fitme-web
python3 - <<'PY'
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.request

expected = {
    'BODY_MODEL_VM_URL': 'http://10.4.2.4:8001/api/avatars',
    'GARMENT_MODEL_VM_URL': 'http://10.4.2.5:8002/api/garments',
    'BODY_MODEL_BLOB_BASE': 'https://fitmemlstdev.blob.core.windows.net/body-glb',
    'GARMENT_MODEL_BLOB_BASE': 'https://fitmemlstdev.blob.core.windows.net/garment-glb',
}
path = Path('/opt/fitme-web/app.env')
if not path.is_file() or path.is_symlink():
    raise SystemExit('Expected a regular app.env; no changes applied')
original = path.read_bytes()
metadata = path.stat()
lines = original.decode('utf-8').splitlines()
pending = dict(expected)
updated = []
for line in lines:
    match = re.match(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=', line)
    key = match.group(1) if match else None
    if key in expected:
        if key in pending:
            updated.append(key+'='+pending.pop(key))
    else:
        updated.append(line)
updated.extend(key+'='+value for key, value in pending.items())
replacement = ('\n'.join(updated).rstrip()+'\n').encode('utf-8')

def command(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError('Command failed; output suppressed to protect configuration')
    return result.stdout

def save(data):
    temporary = path.with_name('app.env.3d-tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.chown(temporary, metadata.st_uid, metadata.st_gid)
    os.replace(temporary, path)

def runtime_matches():
    script = ('import json,os; expected='+repr(expected)+'; '
              'print(json.dumps({key:os.environ.get(key)==value for key,value in expected.items()}))')
    result = command(['docker', 'compose', 'exec', '-T', 'app', 'python', '-c', script])
    return all(json.loads(result).values())

def healthy():
    try:
        with urllib.request.urlopen('http://127.0.0.1:8766/api/health', timeout=10) as response:
            return response.status == 200 and str(json.load(response).get('version')) == '2'
    except Exception:
        return False

changed = replacement != original
recreated = False
if changed:
    directory = Path('/opt/fitme-web/.config-backups')
    directory.mkdir(mode=0o700, exist_ok=True)
    directory.chmod(0o700)
    backup = directory / ('app.env-before-3d-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(original)
    save(replacement)

try:
    config = json.loads(command(['docker', 'compose', 'config', '--format', 'json']))
    environment = config['services']['app'].get('environment', {})
    if any(environment.get(key) != value for key, value in expected.items()):
        raise RuntimeError('Compose overrides the requested 3D settings')
    if changed or not runtime_matches():
        recreated = True
        command(['docker', 'compose', 'up', '-d', '--no-deps', '--force-recreate', '--pull', 'never', '--no-build', 'app'])
    for _ in range(20):
        if healthy():
            break
        time.sleep(3)
    else:
        raise RuntimeError('Web health check failed')
    if not runtime_matches():
        raise RuntimeError('Running app did not receive all four settings')
    with urllib.request.urlopen('http://127.0.0.1:8766/api/v2/model-pair/status', timeout=20) as response:
        if not json.load(response).get('configured'):
            raise RuntimeError('Web 3D configuration check failed')
    print('PASS: all four 3D settings match inside the running web app')
    print('PASS: web health HTTP 200, version 2; 3D configured=true')
    print('Web app recreated:', recreated, '| app.env updated:', changed)
    print('MySQL and Redis were not restarted; image tag and secret values unchanged')
except Exception as error:
    if changed:
        save(original)
    if recreated:
        try:
            command(['docker', 'compose', 'up', '-d', '--no-deps', '--force-recreate', '--pull', 'never', '--no-build', 'app'])
            print('Previous app.env restored and web app recreated')
        except Exception:
            print('ROLLBACK RESTART FAILED: operator intervention required')
    raise SystemExit(type(error).__name__+': configuration application failed; sensitive output suppressed')
PY
