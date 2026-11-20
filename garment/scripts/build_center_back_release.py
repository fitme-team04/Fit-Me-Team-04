# 역할: 확정 상의 형상을 유지한 채 뒷목 기준 입력으로 재등록하고 불변 Blob 배포 묶음을 생성합니다.
import bpy,json,sys,shutil,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from prepare_template import register
from geometry.garment_cages import back_neck_path
from rebuild_cc0_reference import save_anchor_bindings
source=ROOT/'releases/final-garments/models'
out=ROOT/'releases/blob-v19';models=out/'models';models.mkdir(parents=True,exist_ok=True)
old=json.loads((source/'registry.json').read_text())
entry=old['templates']['body_proportional_shirt_v18']
with bpy.data.libraries.load(str(source/entry['blend']),link=False) as (src,dst):dst.objects=[entry['object']]
obj=dst.objects[0];bpy.context.collection.objects.link(obj)
spec=dict(entry['base_spec']);spec['sleeve_length']+=back_neck_path(spec['garment_shoulder_width'])
register(obj,'crewneck',spec,'center_back','body_center_back_v19',models,30.)
path=models/'registry.json';registry=json.loads(path.read_text());new=registry['templates']['body_center_back_v19']
points={key:value['reference'] for key,value in entry['anchor_bindings'].items()}
new.update(revision='19',deformation_policy='shape_preserving_center_back_v1',
    anchor_bindings=save_anchor_bindings(new,points),body_collision_policy='none',
    sleeve_definition='back neck center through shoulder to cuff; template-defined back-top path')
pants=old['templates']['black_midrise_straight_v1'];registry['templates']['black_midrise_straight_v1']=pants
for key in ('blend','binding'):shutil.copy2(source/pants[key],models/pants[key])
path.write_text(json.dumps(registry,indent=2)+'\n')
files={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in models.iterdir() if p.suffix in ('.blend','.npz','.json')}
manifest={'schema_version':1,'release':'2026-11-16-v19','blob_prefix':'',
          'templates':{'crewneck':'body_center_back_v19','slacks':'black_midrise_straight_v1'},'files':files}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(ROOT/'models/bundled_garments.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PASS center-back release prepared; baseline full sleeve cm='+str(spec['sleeve_length']))
