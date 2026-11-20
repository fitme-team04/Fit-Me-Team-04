# 역할: 어깨 맞춤 장면에서 하의를 제거하고 상의 밑단 높이·너비만 신체 허리에 맞춥니다.
import argparse
import json
from pathlib import Path
import sys
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from place_original_garments import smooth, section_width


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-shirt', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    shirt = next(o for o in bpy.context.scene.objects if o.type=='MESH' and len(o.data.vertices)==27642)
    pants = next(o for o in bpy.context.scene.objects if o.type=='MESH' and len(o.data.vertices)==27933)
    bpy.data.objects.remove(pants, do_unlink=True)
    body = next(o for o in bpy.context.scene.objects if o.type=='MESH' and o!=shirt)
    waist = bpy.context.scene.objects['fit_anchor_waist'].matrix_world.translation.copy()
    before_objects = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(args.source_shirt.resolve()), merge_vertices=False)
    bpy.context.view_layer.update()
    added = set(bpy.context.scene.objects)-before_objects
    original = next(o for o in added if o.type=='MESH')
    source = np.array([original.matrix_world @ v.co for v in original.data.vertices])
    assert len(source)==len(shirt.data.vertices)
    for obj in added: bpy.data.objects.remove(obj, do_unlink=True)
    points = np.array([shirt.matrix_world @ v.co for v in shirt.data.vertices])
    body_vertices = np.array([body.matrix_world @ v.co for v in body.data.vertices])
    body.data.calc_loop_triangles()
    faces = np.array([t.vertices[:] for t in body.data.loop_triangles])
    faces = faces[np.max(np.abs(body_vertices[faces,0]-waist.x), axis=1)<.30]
    target_width = section_width(body_vertices, faces, waist.z)
    hem = (source[:,2]<.025)&(np.abs(source[:,0])<.31)
    source_height = float(points[hem,2].min())
    source_width = float(np.ptp(points[hem,0]))
    # Retain hem folds; lift its lowest line to waist and fade out below the chest.
    weight_z = np.clip((1.25-points[:,2])/(1.25-source_height),0,1)
    torso = smooth((.325-np.abs(source[:,0]))/.035)
    moved = points.copy()
    moved[:,2] += (waist.z-source_height)*weight_z*torso
    width_weight = smooth(weight_z)*torso
    moved[:,0] = points[:,0]+((points[:,0]-waist.x)*(target_width/source_width-1))*width_weight
    assert np.max(np.abs(moved[:,1]-points[:,1]))==0
    assert np.max(np.abs(moved[weight_z==0]-points[weight_z==0]))==0
    inverse = shirt.matrix_world.inverted()
    for vertex, point in zip(shirt.data.vertices,moved): vertex.co = inverse @ Vector(point)
    shirt.data.update()
    bpy.ops.object.select_all(action='DESELECT'); shirt.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(output/'shirt.glb'), export_format='GLB', use_selection=True)
    report = {'pants_removed':True,'collision_checked':False,'waist_height_cm':waist.z*100,
        'target_waist_width_cm':target_width*100,'original_hem_height_cm':source_height*100,
        'original_hem_width_cm':source_width*100,'adjusted_hem_min_height_cm':float(moved[hem,2].min()*100),
        'adjusted_hem_width_cm':float(np.ptp(moved[hem,0])*100),'shoulder_region_unchanged':True,
        'depth_unchanged':True,'vertices':len(source)}
    (output/'hem-report.json').write_text(json.dumps(report,indent=2)+'\n')
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'shirt-waist-hem.blend'), compress=True)
    print(json.dumps(report),flush=True)


if __name__=='__main__': main()
