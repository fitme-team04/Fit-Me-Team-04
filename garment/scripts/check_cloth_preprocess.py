# 역할: 실제 Blender에서 충돌용 영역·원본 보존·기준 형태 키 동작을 검사합니다.
"""blender -b --factory-startup -P /app/scripts/check_cloth_preprocess.py

Synthetic fixtures only: no photo, GPU inference, DB, Blob writes or asset edits.
"""
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from geometry.collision_proxy import build_proxy
from core.cloth_geometry import push_out
from core.cloth_contract import mass_settings
from geometry.mesh_validation import BodySurface, validate_mesh
from core.pose_geometry import pose_error

cloth_points=[Vector(p) for p in [(0,0,0),(1,0,0),(0,1,0)]]
body_points=[Vector(p) for p in [(.05,.05,-.05),(.15,.05,.05),(.05,.15,.05)]]
surface=BodySurface(body_points,[(0,1,2)])
assert surface.intersections(cloth_points,[(0,1,2)])['crossing_pairs'] == 1
assert validate_mesh(cloth_points,[(0,1,2)])['valid']
assert not validate_mesh(cloth_points+body_points,[(0,1,2),(3,4,5)])['valid']
landmarks={'fit_shoulder_L':Vector((0,0,0)),'fit_cuff_L':Vector((1,0,0))}
body_landmarks={'fit_shoulder_L':Vector((0,0,0)),'fit_wrist_L':Vector((0,0,-1))}
initial_error=pose_error(landmarks,body_landmarks)
landmarks['fit_cuff_L']=Vector((0,0,-1))
assert pose_error(landmarks,body_landmarks) < initial_error

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=32,radius=.3)
body=bpy.context.object
body.data.calc_loop_triangles()
vertices=[v.co.copy() for v in body.data.vertices]
faces=[tuple(t.vertices) for t in body.data.loop_triangles]
before=[tuple(v.co) for v in body.data.vertices]
proxy,report,_=build_proxy(vertices,faces,[Vector((-.4,-.4,.05)),Vector((.4,.4,.35))])
assert report['selected_faces'] < len(faces)
assert 0 < report['collision_faces'] <= report['selected_faces']
assert before == [tuple(v.co) for v in body.data.vertices]
assert report['simplification_sampled_error_m'] <= .002

original=[(-1.,0.,-.001),(1.,0.,.001),(0.,1.,.001)]
corrected,push=push_out(original,[(0,1),(1,2),(2,0)],[(0,1,2)],
                       lambda p:((p[0],p[1],0.),(0.,0.,1.)))
assert push['accepted'] and push['moved_vertices'] == 1
mesh=bpy.data.meshes.new('TestCloth'); mesh.from_pydata(corrected,[],[(0,1,2)])
cloth=bpy.data.objects.new('TestCloth',mesh); bpy.context.collection.objects.link(cloth)
cloth.shape_key_add(name='Basis',from_mix=False)
key=cloth.shape_key_add(name='FitMeDBRest',from_mix=False)
for item,point in zip(key.data,original): item.co=point
modifier=cloth.modifiers.new('TestCloth','CLOTH'); modifier.settings.rest_shape_key=key
mass=mass_settings('crewneck',len(cloth.data.vertices),{})
modifier.settings.mass=mass['vertex_mass_kg']
assert abs(modifier.settings.mass*len(cloth.data.vertices)-.2) < 1e-6
assert modifier.settings.rest_shape_key == key
assert all((item.co-Vector(point)).length < 1e-6 for item,point in zip(key.data,original))
# Snapshot cleanup must not remove the live simulation's original rest shape.
snapshot=cloth.copy(); snapshot.data=cloth.data.copy(); snapshot.modifiers.clear()
bpy.context.collection.objects.link(snapshot); snapshot.shape_key_clear()
assert cloth.data.shape_keys.key_blocks.get('FitMeDBRest') is not None
assert snapshot.data.shape_keys is None
print('PASS: SAM region/proxy, display preservation, local push-out, DB rest key and independent snapshot')

# Check Blender Armature evaluation and cleanup on the actual starter shirt cage.
from geometry.garment_cages import cage
from core.garment_specs import DEFAULTS
from geometry.garment_pose import candidates, anchor_positions, neck_opening
vertices,faces,anchors,_=cage('crewneck',DEFAULTS['crewneck'],'shoulder')
shirt_mesh=bpy.data.meshes.new('PoseShirt'); shirt_mesh.from_pydata(vertices.tolist(),[],faces.tolist()); shirt_mesh.update()
shirt=bpy.data.objects.new('PoseShirt',shirt_mesh); bpy.context.collection.objects.link(shirt)
original=[v.co.copy() for v in shirt.data.vertices]
source=anchor_positions(anchors); necks=neck_opening(shirt,original)
landmarks={}
for side in ('L','R'):
    landmarks['fit_shoulder_'+side]=source['fit_shoulder_'+side].copy()
    landmarks['fit_wrist_'+side]=source['fit_cuff_'+side].copy()
    landmarks['fit_neck_'+side]=necks[side]+Vector((0,0,.01))
results=list(candidates(shirt,original,anchors,landmarks))
assert len(results) == 3
assert all(len(points) == len(original) for points,_,_ in results)
assert not any(mod.type == 'ARMATURE' for mod in shirt.modifiers)
assert not any(obj.type == 'ARMATURE' for obj in bpy.data.objects)
print('PASS: neck registration and Blender Armature pose candidates, topology and temporary rig cleanup')
