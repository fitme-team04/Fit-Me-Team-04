#!/usr/bin/env bash
# 역할: 신체 VM의 GPU·컨테이너·모델 배포 위치를 비밀 출력 없이 확인합니다.
set -eu
python3 - <<'PY'
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request

def run(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=20)
        return result.stdout.strip() if result.returncode == 0 else 'unavailable'
    except (OSError, subprocess.TimeoutExpired):
        return 'unavailable'

print('GPU:', run(['nvidia-smi','--query-gpu=name,driver_version,memory.total','--format=csv,noheader']))
print('Docker:', run(['docker','version','--format','{{.Server.Version}}']))
print('Containers:', run(['docker','ps','-a','--format','{{.Names}} | {{.Image}} | {{.Status}}']))
print('FitMe images:', run(['docker','images','--filter','reference=*fitme*','--format','{{.Repository}}:{{.Tag}} | {{.Size}}']))
for root in (Path('/opt'), Path('/srv')):
    if root.exists():
        print('Deployment directories:', ', '.join(str(p) for p in root.iterdir() if p.is_dir()))
        for pattern in ('*/compose.yaml','*/docker-compose.yml','*/*/compose.yaml','*/*/docker-compose.yml'):
            for path in root.glob(pattern):
                print('Compose file:', str(path))
for host in ('127.0.0.1','10.4.2.4'):
    try:
        with urllib.request.urlopen('http://'+host+':8001/health', timeout=3) as response:
            data=json.load(response)
            print('Body health:',host,response.status,data.get('status'),data.get('service'))
    except Exception:
        print('Body health unavailable:',host)
print('Disk:', run(['df','-h','/']))
PY
