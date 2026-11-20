# 역할: 실제 SQL에서 확보한 세 브랜드 하의 치수를 정규화해 생성한 작업을 실제 worker로 GLB 출력합니다.
import bpy
import io
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from geometry import garment_worker
from geometry.glb import unpack

jobs=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text(encoding='utf-8'))
os.environ['GARMENT_TEMPLATE_DIR']=str(ROOT/'releases/final-garments/models')
out=ROOT/'releases/final-garments/pants/brand-validation'
out.mkdir(exist_ok=True)
for job in jobs:
    path=out/(job['item_code']+'.glb')
    os.environ['FITME_FD']=str(os.open(path,os.O_CREAT|os.O_TRUNC|os.O_RDWR,0o600))
    with patch.object(sys,'stdin',io.StringIO(json.dumps(job))):garment_worker.main()
    doc,_=unpack(path.read_bytes())
    extras=doc['scenes'][doc.get('scene',0)]['extras']
    assert extras['spec']=={}
    assert extras['template_geometry']['deformation_applied'] is False
    print('PASS real SQL product '+job['item_code']+' '+job['size_label'],flush=True)
(out/'jobs.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
