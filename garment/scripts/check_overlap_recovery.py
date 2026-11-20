# 역할: 초기 신체 관통이 있어도 실제 Blender Cloth 프레임을 실행하는지 검증합니다.
"""blender -b --factory-startup --python-exit-code 3 -P /app/scripts/check_overlap_recovery.py"""
import base64
import hashlib
import math
from pathlib import Path
import sys
import tempfile

import bpy

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from geometry import cloth_fit

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=16,radius=.3)
body=bpy.context.object
anchor=bpy.data.objects.new('fit_anchor_waist',None)
bpy.context.collection.objects.link(anchor)
with tempfile.TemporaryDirectory() as folder:
    path=Path(folder)/'body.glb'
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',export_animations=False)
    data=path.read_bytes()
bpy.data.objects.remove(body,do_unlink=True)
bpy.data.objects.remove(anchor,do_unlink=True)
vertices=[]; faces=[]; count=24
for z in (-.2,0.,.2):
    vertices.extend((.29*math.cos(i*2*math.pi/count),.29*math.sin(i*2*math.pi/count),z) for i in range(count))
for row in range(2):
    for i in range(count):
        a=row*count+i; b=row*count+(i+1)%count
        faces.append((a,b,b+count,a+count))
mesh=bpy.data.meshes.new('OverlappingCloth'); mesh.from_pydata(vertices,[],faces); mesh.update()
obj=bpy.data.objects.new('OverlappingCloth',mesh); bpy.context.collection.objects.link(obj)
bpy.context.view_layer.objects.active=obj
obj.select_set(True)
cloth_fit.FRAMES=3
snapshots=[]
report=cloth_fit.simulate(obj,[{'name':'fit_anchor_waist','translation':[0,0,0]}],
    'slacks',base64.b64encode(data).decode(),hashlib.sha256(data).hexdigest(),
    lambda positions,details:snapshots.append(details.copy()))
assert report['initial_intersection_samples'] > 0, report
assert report['frames'] >= 1, report
assert any(item.get('frames',0) >= 1 for item in snapshots), snapshots
assert report['spring_reference'] == 'original_db_shape'
assert report['status'] == 'failed', 'Three frames must not bypass sustained stability checks'
print('PASS: overlapping initial cloth executes Blender frames and retains failed preview without redefining DB rest')
