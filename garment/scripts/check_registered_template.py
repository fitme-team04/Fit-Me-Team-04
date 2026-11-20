# 역할: 서버 registry가 선택한 실제 의류 원본·DB 변형 메시를 검사합니다.
"""Run with Blender --python-exit-code 3 -P this_file -- [options].

Resolves GARMENT_TEMPLATE_DIR exactly like the API. Never rewrites assets.
"""
import argparse
import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from geometry.template_catalog import resolve_template, model_root
from geometry.template_binding import deform

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--template-id',default='crewneck_v1')
parser.add_argument('--kind',choices=('crewneck','slacks'),default='crewneck')
parser.add_argument('--spec-json',type=Path,help='Optional DB spec JSON; otherwise registered base_spec')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
entry=resolve_template(args.template_id,args.kind)
spec=json.loads(args.spec_json.read_text(encoding='utf-8')) if args.spec_json else entry['base_spec']
with bpy.data.libraries.load(entry['blend_path'],link=False) as (source,dest):
    if entry['object'] not in source.objects: raise ValueError('Registered garment object is missing')
    dest.objects=[entry['object']]
obj=dest.objects[0]; bpy.context.collection.objects.link(obj)
_,metrics,info=deform(obj,entry,spec,entry.get('sleeve_basis','shoulder' if args.kind=='crewneck' else 'none'))
report={'registry':str(model_root()/'registry.json'),'template_id':args.template_id,
        'revision':entry.get('revision'),'blend_path':entry['blend_path'],
        'spec':spec,'cage_metrics':metrics,'geometry':info}
print('FITME_TEMPLATE_AUDIT '+json.dumps(report,allow_nan=False),flush=True)
if not info['source_mesh_quality']['valid'] or not info['db_mesh_quality']['valid']:
    raise ValueError('Registered template quality failed; inspect FITME_TEMPLATE_AUDIT')
