# 역할: 검증된 GLB를 배포용 Blender 버전에서 다시 저장하고 의류 바인딩을 재생성합니다.
import argparse
import json
from pathlib import Path
import sys

import bpy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from prepare_template import register


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--registry',required=True,type=Path)
    parser.add_argument('--glbs',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    source=json.loads(args.registry.read_text())
    for template_id,entry in source['templates'].items():
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        bpy.ops.import_scene.gltf(filepath=str((args.glbs/template_id/'model.glb').resolve()),merge_vertices=True)
        bpy.context.view_layer.update()
        original=next(obj for obj in bpy.context.scene.objects if obj.type=='MESH')
        mesh=bpy.data.meshes.new_from_object(original.evaluated_get(bpy.context.evaluated_depsgraph_get()),
            preserve_all_data_layers=True,depsgraph=bpy.context.evaluated_depsgraph_get())
        mesh.transform(original.matrix_world)
        for obj in list(bpy.context.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
        obj=bpy.data.objects.new('GarmentMesh',mesh);bpy.context.collection.objects.link(obj)
        registration=register(obj,entry['kind'],entry['base_spec'],entry['sleeve_basis'],template_id,args.output,25.)
        path=args.output/'registry.json'
        registry=json.loads(path.read_text())
        registry['templates'][template_id].update({key:entry[key] for key in
            ('anchor_bindings','reference_body_sha256','revision')})
        registry['templates'][template_id]['saved_with_blender']=bpy.app.version_string
        path.write_text(json.dumps(registry,indent=2)+'\n')
        print('PASS: template saved with Blender '+bpy.app.version_string+' '+template_id,flush=True)


if __name__=='__main__':
    main()
