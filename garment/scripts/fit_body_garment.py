# 역할: 임의의 실제 신체 NPZ와 의류 실측 JSON을 받아 체형 추종·관통 보정 후 통과한 GLB만 출력합니다.
import argparse
import json
import os
from pathlib import Path
import sys
import bpy
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from core.garment_specs import validate_spec
from geometry.template_catalog import resolve_template
from geometry.template_binding import geometry,deform
from geometry.body_clearance import follow_body,require_clear
from fit_uploaded_garments import shell_clearances
from rebuild_cc0_reference import clear_body,inspect
from project_garment_surface import project_surface


def main():
    parser=argparse.ArgumentParser()
    for name in ('models','reference-body-glb','body-npz','binding-npz','spec-json','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--template-id',required=True);parser.add_argument('--kind',choices=('crewneck','slacks'),required=True)
    parser.add_argument('--max-correction-cm',type=float,default=3.,help='Engineering review guard, not a physical fabric limit')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    if (output/'model.glb').exists():raise ValueError('Use a fresh job output directory to prevent stale model reuse')
    os.environ['GARMENT_TEMPLATE_DIR']=str(args.models.resolve())
    entry=resolve_template(args.template_id,args.kind)
    spec=validate_spec(args.kind,json.loads(args.spec_json.read_text()),entry['sleeve_basis'])
    with np.load(args.binding_npz,allow_pickle=False) as b:
        ids=b['ids'];weights=b['weights'];reference=b['reference_body'];faces_body=b['body_faces']
    with np.load(args.body_npz,allow_pickle=False) as b:
        target=b['vertices'];target_faces=b['faces']
    if not np.array_equal(target_faces,faces_body):raise ValueError('Body topology changed; rebind required')
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(args.reference_body_glb.resolve()))
    placement=bpy.context.scene.objects['fit_anchor' if args.kind=='crewneck' else 'fit_anchor_waist'].matrix_world.copy()
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    with bpy.data.libraries.load(entry['blend_path'],link=False) as (src,dst):dst.objects=[entry['object']]
    obj=dst.objects[0];bpy.context.collection.objects.link(obj)
    original,faces=geometry(obj)
    world=np.array([placement@Vector(p) for p in original])
    targets=shell_clearances(world,faces,reference,faces_body)
    deform(obj,entry,spec,entry['sleeve_basis']);local,_=geometry(obj)
    followed=follow_body(np.array([placement@Vector(p) for p in local]),reference,target,ids,weights)
    protect_feet=args.kind=='slacks' and spec['inseam']>entry['base_spec']['inseam']*1.05
    fitted,faces,iterations,correction=project_surface(obj,followed,faces,target,faces_body,targets,protect_feet=protect_feet)
    report={'check':inspect(fitted,faces,target,faces_body),'iterations':iterations,
            'maximum_correction_cm':correction,'spec':spec}
    report['requires_review']=report['maximum_correction_cm']>args.max_correction_cm
    # Always retain failure diagnostics. Do not emit a new model on failure.
    (output/'clearance-report.json').write_text(json.dumps(report,indent=2)+'\n')
    require_clear(report['check'])
    if report['requires_review']:raise ValueError('Correction exceeds review guard; output blocked to avoid silent shape damage')
    obj.data.vertices.foreach_set('co',fitted.ravel());obj.data.update()
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(output/'model.glb'),export_format='GLB',use_selection=True)
    print('PASS: body-aware garment exported',flush=True)


if __name__=='__main__':main()
