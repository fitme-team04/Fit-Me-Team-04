# 역할: 수정 의류를 실제 서비스 경로로 GLB로 내보내고 기준 신체 정렬·관통을 재검증합니다.
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import subprocess
from unittest.mock import patch

import bpy
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from geometry import garment_worker
from geometry.mesh_anchors import extract,garment_fitting
from rebuild_cc0_reference import inspect,vertices_world,triangles


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--models',required=True,type=Path)
    parser.add_argument('--body',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--template-id')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    os.environ['GARMENT_TEMPLATE_DIR']=str(args.models.resolve())
    registry=json.loads((args.models/'registry.json').read_text())
    if args.template_id is None:
        # Match production's one-Blender-process-per-job lifecycle. Older Blender
        # releases can crash when repeatedly deleting/reimporting glTF scenes.
        for template_id in registry['templates']:
            subprocess.run([bpy.app.binary_path,'-b','-Y','--factory-startup','--python-exit-code','1',
                '--python-expr','import sys; sys.path[:0] = '+repr(sys.path),'-P',str(Path(__file__).resolve()),
                '--','--models',str(args.models.resolve()),'--body',str(args.body.resolve()),
                '--output',str(output),'--template-id',template_id],check=True)
        return
    if args.template_id not in registry['templates']:
        raise ValueError('Unknown template ID')
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(args.body.resolve()))
    body=next(obj for obj in bpy.context.scene.objects if obj.type=='MESH')
    body_vertices=vertices_world(body);body_faces=triangles(body)
    anchors_body={obj.name:obj.matrix_world.copy() for obj in bpy.context.scene.objects if obj.name.startswith('fit_')}
    report_path=output/'delivered-glb-validation.json'
    report=json.loads(report_path.read_text()) if report_path.exists() else {}
    for template_id,entry in registry['templates'].items():
        if args.template_id and template_id!=args.template_id:
            continue
        folder=output/template_id;folder.mkdir(exist_ok=True)
        path=folder/'model.glb'
        pending=folder/'model.pending.glb'
        job={'recipe':{'kind':entry['kind'],'template_id':template_id,'sleeve_basis':entry['sleeve_basis']},
             'spec':entry['base_spec']}
        os.environ['FITME_FD']=str(os.open(pending,os.O_CREAT|os.O_TRUNC|os.O_RDWR,0o600))
        with patch.object(sys,'stdin',io.StringIO(json.dumps(job))):
            garment_worker.main()
        os.replace(pending,path)
        blob=path.read_bytes()
        parent,anchors,_=extract(blob,'garments')
        for name,binding in entry['anchor_bindings'].items():
            if name not in anchors:
                assert name=='fit_anchor' and entry['kind']=='slacks'
                continue
            x,y,z=binding['reference']
            assert np.linalg.norm(np.array(anchors[name]['translation'])-[x,z,-y])<1e-6
        metadata={'schema_version':1,'model':'model.glb','model_sha256':hashlib.sha256(blob).hexdigest(),
            'space':'glTF parent-local','parent_node':parent,'unit':'m','up_axis':'+Y',
            'quaternion_order':'xyzw','anchors':anchors,'garment':garment_fitting(blob)}
        (folder/'anchors.json').write_text(json.dumps(metadata,indent=2)+'\n')
        # Reimport the actual delivered GLB, including its coordinate transforms.
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        bpy.ops.import_scene.gltf(filepath=str(path))
        bpy.context.view_layer.update()
        mesh=next(obj for obj in bpy.context.scene.objects if obj.type=='MESH')
        name='fit_anchor' if entry['kind']=='crewneck' else 'fit_anchor_waist'
        inverse=anchors_body[name].inverted()
        local_body=np.array([inverse @ Vector(point) for point in body_vertices])
        result=inspect(vertices_world(mesh),triangles(mesh),local_body,body_faces)
        assert result['body_triangle_intersections']==0,result
        assert all(result[key]['inside']==0 for key in ('vertices','edge_midpoints','triangle_centroids')),result
        assert result['topology']['degenerate_triangles']==0
        result['sha256']=metadata['model_sha256'];result['glb_bytes']=len(blob)
        report[template_id]=result
        print('PASS: delivered GLB '+template_id+' has no detected body intersection',flush=True)
    report_path.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
