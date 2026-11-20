#!/usr/bin/env bash
# 역할: SAM 체크포인트와 측정 가이드를 검사한 뒤 직접 SAM 메시 API를 빌드·기동합니다.
set -euo pipefail
cd /opt/fitme-avatar
python3 - <<'PY'
from pathlib import Path
root=Path('.')
required=['models/mhr_model.pt','models/fitme_depth_fixed.blend','models/a_pose.npz','models/sam_body.npz',
          'models/sam/model.ckpt','models/sam/model_config.yaml',
          'models/vitdet/model_final_f05665.pkl','models/moge/model.pt']
missing=[name for name in required if not (root/name).is_file()]
if missing:
    print('BLOCKED: missing real inference prerequisites:')
    for name in missing: print(' - '+name)
    raise SystemExit(2)
print('PASS: inference prerequisite files present')
PY
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
docker compose -f compose.yaml config -q
docker compose -f compose.yaml build
docker compose -f compose.yaml up -d
docker compose -f compose.yaml exec -T avatar \
    /opt/conda/bin/python /app/scripts/check_assets.py --models /models --with-checkpoints
sam_mode=$(docker compose -f compose.yaml exec -T avatar python -c \
    'from core.sam_runtime import runtime_mode; print(runtime_mode())')
if [[ "$sam_mode" == "oneshot" ]]; then
    docker compose -f compose.yaml exec -T avatar \
        /opt/conda/bin/python /app/src/inference/sam_reference.py check
else
    echo 'Resident SAM validates the GPU model at API startup; skipping duplicate GPU load'
fi
python3 - <<'PY'
import json,time,urllib.request
for _ in range(30):
    try:
        with urllib.request.urlopen('http://10.4.2.4:8001/health',timeout=5) as response:
            if response.status==200 and json.load(response).get('status')=='ok':
                print('PASS: body API health; ready for explicit photograph test')
                break
    except Exception:
        pass
    time.sleep(2)
else:
    raise SystemExit('FAIL: body API health timeout')
PY
