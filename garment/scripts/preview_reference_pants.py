# 역할: 손상 없는 바지 원형을 참고 사진처럼 여유 있는 검정 일자핏으로 조정하고 착용 이미지를 생성합니다.
import bpy
import json
import sys
import argparse
from pathlib import Path
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from rebuild_cc0_reference import vertices_world, triangles, inspect, clear_body, boundary_loops
from repair_reference_outfit import contours
from geometry.body_clearance import require_clear

parser = argparse.ArgumentParser()
parser.add_argument('--mid-rise', action='store_true')
parser.add_argument('--slim-hips', action='store_true')
parser.add_argument('--straight-calves', action='store_true')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
if args.slim_hips and not args.mid_rise:
    parser.error('--slim-hips requires --mid-rise')
if args.straight_calves and not args.slim_hips:
    parser.error('--straight-calves requires --slim-hips')
out = ROOT / ('.cache/reference-black-pants-midrise-hips' if args.slim_hips else '.cache/reference-black-pants-midrise' if args.mid_rise else '.cache/reference-black-pants')
if args.straight_calves:
    out = ROOT / '.cache/reference-black-pants-straight'
out.mkdir(exist_ok=True)
body = bpy.data.objects['ReferenceBody']
pants = bpy.data.objects['Slacks']
bpy.data.objects['WhiteTshirt'].hide_render = True
v = vertices_world(pants)
f = triangles(pants)
original = v.copy()
progress = np.clip((.70 - v[:, 2]) / .65, 0, 1)
for side in (-1, 1):
    ids = np.flatnonzero(side * v[:, 0] > 0)
    center = side * .118
    v[ids, 0] = center + (v[ids, 0] - center) * (1 - .10 * progress[ids])
waist_report = {}
if args.mid_rise:
    # 역할: 허리선을 3cm 낮추고 해당 높이의 실제 신체 단면에 약 5mm 여유를 더해 허리 밴드를 맞춥니다.
    waistband = max(boundary_loops(f), key=lambda ids: v[ids, 2].mean())
    old_top = float(v[waistband, 2].mean())
    new_top = old_top - .03
    blend = np.clip((v[:, 2] - (old_top-.18))/.18, 0, 1)
    blend = blend*blend*(3-2*blend)
    v[:, 2] -= .03*blend
    section = max(contours(vertices_world(body), triangles(body), new_top), key=len)
    center = (section.min(0)+section.max(0))/2
    radius = (section.max(0)-section.min(0))/2
    old_ring = v[waistband]
    old_center = (old_ring.min(0)+old_ring.max(0))/2
    old_radius = (old_ring.max(0)-old_ring.min(0))/2
    target = center[:2] + (v[:, :2]-old_center[:2])/old_radius[:2]*(radius[:2]+.005)
    v[:, :2] = v[:, :2]*(1-blend[:, None])+target*blend[:, None]
    waist_report = {'old_height_cm': old_top*100, 'new_height_cm': new_top*100,
        'body_width_at_new_height_cm': float(2*radius[0]*100), 'target_width_cm': float((2*radius[0]+.01)*100)}
hip_report = {}
if args.slim_hips:
    # 역할: 골반 옆선의 과한 여유만 줄이고 허리·다리 아래쪽은 유지합니다.
    levels = np.linspace(.45, new_top-.025, 90)
    widths = []
    for level in levels:
        rings = contours(v, f, float(level))
        widths.append(max(float(np.max(np.abs(ring[:, 0]))) for ring in rings))
    half_target = np.interp(levels, [.45, .64, .72, .84, new_top-.025], [.205, .195, .188, .179, .161])
    factors = np.minimum(1., half_target / np.asarray(widths))
    fade = np.clip((levels-.45)/.12, 0, 1)*np.clip((new_top-.025-levels)/.025, 0, 1)
    factors = 1-(1-factors)*fade
    before = v.copy()
    v[:, 0] *= np.interp(v[:, 2], levels, factors, left=1., right=1.)
    hip_report['maximum_inset_per_side_cm'] = float(np.max(np.abs(before[:, 0])-np.abs(v[:, 0]))*100)
calf_report = {}
if args.straight_calves:
    # 역할: 종아리에서 다시 벌어지는 옆선을 줄여 무릎과 밑단을 완만한 일자선으로 연결합니다.
    levels = np.linspace(float(v[:, 2].min())+.005, .72, 100)
    widths = np.array([max(float(np.max(np.abs(ring[:, 0]))) for ring in contours(v, f, float(z))) for z in levels])
    target_widths = np.interp(levels, [.05, .45, .64, .72], [.230, .210, .194, .188])
    factors = np.minimum(1., target_widths/widths)
    before = v.copy()
    v[:, 0] *= np.interp(v[:, 2], levels, factors, right=1.)
    calf_report['maximum_inset_per_side_cm'] = float(np.max(np.abs(before[:, 0])-np.abs(v[:, 0]))*100)
v, iterations = clear_body(v, f, vertices_world(body), triangles(body), margin=.003, minimum_clearance=.0012)
check = inspect(v, f, vertices_world(body), triangles(body))
require_clear(check)
inverse = pants.matrix_world.inverted()
local = np.array([inverse @ Vector(point) for point in v])
pants.data.vertices.foreach_set('co', local.ravel())
pants.data.update()
if args.mid_rise:
    waist_report['actual_width_cm'] = float(np.ptp(v[waistband, 0])*100)
for obj in (body, pants):
    obj.color = (.65, .65, .65, 1) if obj == body else (.018, .024, .030, 1)
for material in pants.data.materials:
    material.diffuse_color = pants.color
    if material.use_nodes:
        shader = material.node_tree.nodes.get('Principled BSDF')
        if shader:
            shader.inputs['Base Color'].default_value = pants.color
            shader.inputs['Roughness'].default_value = .95
scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'OBJECT'
scene.display.shading.background_type = 'WORLD'
scene.world.color = (.18, .18, .18)
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = False
scene.display.shading.show_specular_highlight = False
scene.display.render_aa = '32'
scene.render.resolution_x = 900
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
camera_data = bpy.data.cameras.new('PantsPreview')
camera = bpy.data.objects.new('PantsPreview', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = 'ORTHO'
camera_data.ortho_scale = 2.05
for name, location in [('front', (0, -4, .95)), ('side', (4, 0, .95)), ('angle', (3, -4, 1.6))]:
    camera.location = location
    camera.rotation_euler = (Vector((0, 0, .88)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(out / (name + '.png'))
    bpy.ops.render.render(write_still=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'reference-fitting.blend'), compress=True)
bpy.ops.object.select_all(action='DESELECT')
pants.select_set(True)
bpy.context.view_layer.objects.active = pants
bpy.ops.export_scene.gltf(filepath=str(out / 'model.glb'), export_format='GLB', use_selection=True)
(out / 'report.json').write_text(json.dumps({'body_check': check, 'clearance_iterations': iterations,
    'waist_adjustment': waist_report,
    'hip_adjustment': hip_report,
    'calf_adjustment': calf_report,
    'source': 'grey-wide-slacks-v5', 'style': 'relaxed straight black pants',
    'maximum_shift_mm': float(np.linalg.norm(v-original, axis=1).max()*1000)}, indent=2))
