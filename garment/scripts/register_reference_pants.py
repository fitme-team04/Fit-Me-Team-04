# 역할: 확정한 미드라이즈 바지를 서비스용 Blender 템플릿과 치수 바인딩으로 등록합니다.
import bpy
import json
import sys
from pathlib import Path
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from prepare_template import register
from rebuild_cc0_reference import vertices_world, save_anchor_bindings

out = ROOT/'.cache/blob-pants-release'
models = out/'models'
models.mkdir(parents=True, exist_ok=True)
pants = bpy.data.objects['Slacks']
body = bpy.data.objects['ReferenceBody']
bpy.ops.import_scene.gltf(filepath=str(ROOT/'.cache/tripo-fit-v10/bodies/baseline.glb'))
placement = bpy.data.objects['fit_anchor_waist'].matrix_world.copy()
world = vertices_world(pants)
local = np.array([placement.inverted() @ Vector(point) for point in world])
pants.data.vertices.foreach_set('co', local.ravel())
pants.matrix_world.identity()
pants.data.update()
spec = {'waist_width':42., 'hip_width':52., 'front_rise':30., 'inseam':72.,
        'thigh_width':32., 'knee_width':26., 'hem_width':25.}
template_id = 'black_midrise_straight_v1'
register(pants, 'slacks', spec, 'none', template_id, models, 30.)
path = models/'registry.json'
registry = json.loads(path.read_text())
entry = registry['templates'][template_id]
points = {'fit_anchor_waist': np.zeros(3)}
entry.update(revision='1', anchor_bindings=save_anchor_bindings(entry, points),
             source_style='approved midrise straight pants',
             measurement_note='base_spec defines the deformation cage; custom mesh surface measurements differ')
path.write_text(json.dumps(registry, indent=2)+'\n')
(out/'garment-spec.json').write_text(json.dumps(spec, indent=2)+'\n')
print('REGISTERED '+template_id)
