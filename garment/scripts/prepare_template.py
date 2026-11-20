# 역할: 외부 Blender 의류를 정리하고 바인딩·등록 정보를 생성합니다.
"""Run with Blender -b -Y --factory-startup -P scripts/prepare_template.py -- ..."""
import argparse
import json
import re
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import bpy
import bmesh
from mathutils import Matrix
import numpy as np
from core.garment_specs import validate_spec, complete_slacks_spec
from geometry.template_binding import bind
from geometry.garment_cages import cage
from geometry.cloth_fit import support_group


def register(obj,kind,spec,basis,template_id,directory,max_distance_cm=8):
    if not re.fullmatch(r'[a-z0-9_-]{1,64}',template_id):raise ValueError('Invalid template ID')
    reference_spec=spec
    spec=validate_spec(kind,spec,basis)
    binding_spec=complete_slacks_spec(spec,reference_spec) if kind=='slacks' else spec
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=True)
    obj.name='GarmentMesh';obj.data.name='GarmentMesh'
    # Recalculate consistent normals without changing vertex ordering or UV layers.
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    obj.data.update()
    if not obj.data.vertices or not obj.data.polygons:raise ValueError('Empty garment mesh')
    if len(obj.data.vertices)>250000:raise ValueError('Template exceeds 250,000 vertices')
    blend_name=template_id+'.blend';binding_name=template_id+'.npz'
    report=bind(obj,kind,binding_spec,basis,directory/binding_name,max_distance_cm)
    _,_,anchors,_=cage(kind,binding_spec,basis)
    support_group(obj,[v.co.copy() for v in obj.data.vertices],kind,anchors)
    bpy.context.scene.unit_settings.system='METRIC'
    bpy.context.scene.unit_settings.scale_length=1
    bpy.ops.file.pack_all()
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(directory/blend_name),compress=True)
    registry_path=directory/'registry.json'
    registry=json.loads(registry_path.read_text()) if registry_path.exists() else {'schema_version':1,'templates':{}}
    registry['templates'][template_id]={'kind':kind,'blend':blend_name,'binding':binding_name,
        'object':'GarmentMesh','revision':'1','base_spec':spec,'sleeve_basis':basis,
        'registration':report}
    registry_path.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--object',required=True)
    parser.add_argument('--kind',required=True,choices=['crewneck','slacks'])
    parser.add_argument('--base-json',required=True,type=Path)
    parser.add_argument('--sleeve-basis',default='shoulder',choices=['shoulder','center_back','none'])
    parser.add_argument('--template-id',required=True)
    parser.add_argument('--output-dir',required=True,type=Path)
    parser.add_argument('--units',choices=['m','cm'],default='m')
    parser.add_argument('--max-distance-cm',type=float,default=8)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    registry=args.output_dir/'registry.json'
    if registry.exists() and args.template_id in json.loads(registry.read_text())['templates']:
        raise ValueError('Template ID already exists; use a new version ID')
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    with bpy.data.libraries.load(str(args.source.resolve()),link=False) as (src,dst):
        if args.object not in src.objects:raise ValueError('Object missing in source .blend')
        dst.objects=[args.object]
    source=dst.objects[0];bpy.context.collection.objects.link(source)
    if source.constraints or any(m.type=='ARMATURE' for m in source.modifiers):
        raise ValueError('Bake the posed rig/constraints to a static mesh in the source file first')
    bpy.context.view_layer.update()
    evaluated=source.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,
                                       depsgraph=bpy.context.evaluated_depsgraph_get())
    mesh.transform(source.matrix_world)
    if args.units=='cm':mesh.transform(Matrix.Scale(.01,4))
    obj=bpy.data.objects.new('PreparedGarment',mesh);bpy.context.collection.objects.link(obj)
    bpy.data.objects.remove(source,do_unlink=True)
    if any(image.source=='FILE' and not image.packed_file and not image.has_data for image in bpy.data.images):
        raise ValueError('Source has missing image textures; pack textures in Blender first')
    report=register(obj,args.kind,json.loads(args.base_json.read_text()),args.sleeve_basis,
                    args.template_id,args.output_dir,args.max_distance_cm)
    print(json.dumps({'template_id':args.template_id,'registered':report}))

if __name__=='__main__':main()
