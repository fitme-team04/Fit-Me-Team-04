# 역할: 최종 상·하의 GLB를 기준 신체에 배치해 의류 간 교차와 표면 간격을 검사합니다.
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from rebuild_cc0_reference import vertices_world,triangles,tree


def samples(vertices,faces):
    edges=np.unique(np.sort(np.vstack([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)
    return np.vstack((vertices,vertices[edges].mean(1),vertices[faces].mean(1)))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--body',required=True,type=Path)
    parser.add_argument('--models',required=True,type=Path)
    parser.add_argument('--glbs',required=True,type=Path)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(args.body.resolve()))
    anchors={obj.name:obj.matrix_world.copy() for obj in bpy.context.scene.objects if obj.name.startswith('fit_')}
    registry=json.loads((args.models/'registry.json').read_text())
    meshes={}
    for name,entry in registry['templates'].items():
        before=set(bpy.context.scene.objects)
        bpy.ops.import_scene.gltf(filepath=str((args.glbs/name/'model.glb').resolve()))
        bpy.context.view_layer.update()
        obj=next(obj for obj in set(bpy.context.scene.objects)-before if obj.type=='MESH')
        kind=entry['kind'];placement=anchors['fit_anchor' if kind=='crewneck' else 'fit_anchor_waist']
        vertices=np.array([placement @ Vector(p) for p in vertices_world(obj)])
        meshes[kind]=(vertices,triangles(obj))
    top,top_faces=meshes['crewneck'];pants,pants_faces=meshes['slacks']
    top_tree=tree(top,top_faces);pants_tree=tree(pants,pants_faces)
    overlap=top_tree.overlap(pants_tree)
    distances=[]
    for points,obstacle in [(samples(top,top_faces),pants_tree),(samples(pants,pants_faces),top_tree)]:
        distances.extend(obstacle.find_nearest(Vector(point))[3] for point in points)
    result={'garment_triangle_intersections':len(overlap),
        'minimum_sampled_garment_clearance_mm':float(min(distances)*1000),
        'sample_count':len(distances),'blender_version':bpy.app.version_string}
    (args.glbs/'outfit-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    if overlap:raise ValueError('Delivered garments intersect')
    print('PASS: delivered shirt/pants intersections=0, sampled clearance='+str(result['minimum_sampled_garment_clearance_mm'])+' mm',flush=True)


if __name__=='__main__':main()
