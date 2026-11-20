# 역할: 모델 파일의 크기와 SHA-256 명세를 갱신합니다.
"""Record files only after regenerating and reviewing pose/binding together."""
import argparse,hashlib,json
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--models',default='/models');a=ap.parse_args();root=Path(a.models)
files={}
for name in ['fitme_depth_fixed.blend','mhr_model.pt','a_pose.npz','sam_body.npz']:
    p=root/name
    with p.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
    files[name]={'bytes':p.stat().st_size,'sha256':h}
(root/'bundled_assets.json').write_text(json.dumps({'files':files,'source':'Locally regenerated; review pose and binding reports.'},indent=2))
print('Recorded current asset hashes')
