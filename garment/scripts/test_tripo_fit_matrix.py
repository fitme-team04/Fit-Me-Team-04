# 역할: 실제 의류 케이지 변형과 체형 추종·관통 보정을 적용해 29개 신체 치수와 의류 치수의 회귀 행렬을 검사합니다.
import argparse
import json
import os
from pathlib import Path
import sys
import time
import bpy
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from geometry.template_catalog import resolve_template
from geometry.template_binding import geometry,deform
from geometry.body_clearance import bind_body,follow_body,require_clear
from rebuild_cc0_reference import inspect,clear_body,vertices_world
from fit_uploaded_garments import shell_clearances
from project_garment_surface import project_surface


def main():
    parser=argparse.ArgumentParser()
    for name in ('models','bodies','reference-body','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--retry-failed',action='store_true')
    parser.add_argument('--only-kind',choices=('crewneck','slacks'))
    parser.add_argument('--quick',action='store_true',help='Baseline and two joint bodies, plus garment sizing checks')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    os.environ['GARMENT_TEMPLATE_DIR']=str(args.models.resolve())
    registry=json.loads((args.models/'registry.json').read_text())
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(args.reference_body.resolve()))
    anchors={o.name:o.matrix_world.copy() for o in bpy.context.scene.objects if o.name.startswith('fit_')}
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    with np.load(args.bodies/'baseline.npz') as b:reference=b['vertices'].copy();body_faces=b['faces'].copy()
    inputs=json.loads((args.bodies/'body-test-inputs.json').read_text())
    report_path=output/'matrix-results.json'
    report=json.loads(report_path.read_text()) if args.resume and report_path.exists() else {'synthetic':True,'body_range':'individual +/-5%; joint +/-5%',
        'garment_range':'individual +/-10%; joint +/-10%','body_collision_only':True,'cases':[]}
    if args.retry_failed:
        failed=[c for c in report['cases'] if not c['ok']]
        history_path=output/'previous-failed-attempts.json'
        history=json.loads(history_path.read_text()) if history_path.exists() else []
        history_path.write_text(json.dumps(history+failed,indent=2)+'\n')
        report['cases']=[c for c in report['cases'] if c['ok']]
    completed={c['id'] for c in report['cases']}
    for template_id,entry_data in registry['templates'].items():
        if args.only_kind and entry_data['kind']!=args.only_kind:continue
        entry=resolve_template(template_id,entry_data['kind']);kind=entry['kind']
        with bpy.data.libraries.load(entry['blend_path'],link=False) as (src,dst):dst.objects=[entry['object']]
        obj=dst.objects[0];bpy.context.collection.objects.link(obj)
        original,faces=geometry(obj)
        source_mesh=obj.data.copy()
        placement=anchors['fit_anchor' if kind=='crewneck' else 'fit_anchor_waist']
        world=np.array([placement@Vector(p) for p in original])
        ids,weights=bind_body(world,reference,body_faces)
        np.savez_compressed(output/(template_id+'-body-binding.npz'),ids=ids,weights=weights,reference_body=reference,body_faces=body_faces)
        targets=shell_clearances(world,faces,reference,body_faces)
        cases=[(c['name'],c['name'],dict(entry['base_spec'])) for c in inputs['cases'] if c['ok'] and (not args.quick or c['name']=='baseline' or c['name'].startswith('joint_'))]
        if args.quick:report['body_range']='baseline and two joint +/-5% bodies only; not individual 29-field checks'
        report['only_kind']=args.only_kind
        for key in entry['base_spec']:
            for factor in (.9,1.1):
                spec=dict(entry['base_spec']);spec[key]*=factor
                cases.append(('garment_'+key+'_'+str(factor),'baseline',spec))
        for factor in (.9,1.1):cases.append(('garment_joint_'+str(factor),'joint_'+str(.95 if factor<1 else 1.05),{k:v*factor for k,v in entry['base_spec'].items()}))
        for case_name,body_name,spec in cases:
            case_id=template_id+':'+case_name
            if case_id in completed:continue
            start=time.monotonic();result={'id':case_id,'body':body_name,'spec':spec}
            try:
                with np.load(args.bodies/(body_name+'.npz')) as b:target=b['vertices'].copy()
                old_mesh=obj.data;obj.data=source_mesh.copy();bpy.data.meshes.remove(old_mesh)
                obj.matrix_world.identity();obj.data.vertices.foreach_set('co',original.ravel());obj.data.update()
                deform(obj,entry,spec,entry['sleeve_basis'])
                local,_=geometry(obj)
                sized=np.array([placement@Vector(p) for p in local])
                followed=follow_body(sized,reference,target,ids,weights)
                protect_feet=kind=='slacks' and spec['inseam']>entry['base_spec']['inseam']*1.05
                corrected,case_faces,iterations,correction=project_surface(obj,followed,faces,target,body_faces,targets,protect_feet=protect_feet)
                check=inspect(corrected,case_faces,target,body_faces)
                result.update(check=check,iterations=iterations,maximum_correction_cm=correction)
                require_clear(check)
                result['ok']=True
                if case_name=='baseline' or case_name.startswith(('joint_','garment_joint_')):
                    folder=output/case_name;folder.mkdir(exist_ok=True)
                    obj.data.vertices.foreach_set('co',corrected.ravel());obj.data.update()
                    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
                    bpy.ops.export_scene.gltf(filepath=str(folder/(kind+'.glb')),export_format='GLB',use_selection=True)
            except Exception as exc:
                result.update(ok=False,error=str(exc))
            result['seconds']=round(time.monotonic()-start,2)
            report['cases'].append(result)
            report['summary']={'total':len(report['cases']),'passed':sum(c['ok'] for c in report['cases']),
                'failed':sum(not c['ok'] for c in report['cases'])}
            report_path.write_text(json.dumps(report,indent=2)+'\n')
            print('FITME_MATRIX '+json.dumps({k:result.get(k) for k in ('id','ok','seconds','iterations','maximum_correction_cm','error')}),flush=True)
        bpy.data.objects.remove(obj,do_unlink=True)


if __name__=='__main__':main()
