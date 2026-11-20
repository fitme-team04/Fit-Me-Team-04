# 역할: 원본 의류의 어깨·허리 위치를 맞추며, 선택적으로 해당 부위 너비만 국소 보정하고 길이·두께를 유지합니다.
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import bpy
from mathutils import Vector


def main():
    parser = argparse.ArgumentParser()
    for name in ('shirt', 'pants', 'body', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--width-only', action='store_true', help='Adjust shoulder/waist width locally; preserve length and depth')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(args.body.resolve()))
    bpy.context.view_layer.update()
    anchors = {obj.name: obj.matrix_world.copy() for obj in bpy.context.scene.objects if obj.name.startswith('fit_')}
    shoulder = (anchors['fit_shoulder_L'].translation + anchors['fit_shoulder_R'].translation) / 2
    waist = anchors['fit_anchor_waist'].translation
    body = next(obj for obj in bpy.context.scene.objects if obj.type == 'MESH')
    body_vertices = np.array([body.matrix_world @ v.co for v in body.data.vertices])
    body.data.calc_loop_triangles()
    body_faces = np.array([t.vertices[:] for t in body.data.loop_triangles])
    report = {'mode': 'translation_only', 'size_adjustment': False, 'mesh_deformation': False,
              'rotation_adjustment': False, 'collision_checked': False, 'garments': {}}
    if args.width_only:
        report.update(mode='local_width_and_translation', size_adjustment='shoulder_or_waist_width_only', mesh_deformation=True)
    # Source landmarks are in Blender world metres after unchanged glTF import.
    for name, path, source, target in (
        ('shirt', args.shirt, Vector((0, .02, .86)), shoulder),
        ('pants', args.pants, Vector((0, 0, .98)), waist),
    ):
        previous = set(bpy.context.scene.objects)
        bpy.ops.import_scene.gltf(filepath=str(path.resolve()), merge_vertices=False)
        bpy.context.view_layer.update()
        objects = set(bpy.context.scene.objects) - previous
        meshes = [obj for obj in objects if obj.type == 'MESH']
        original = {obj: [tuple(v.co) for v in obj.data.vertices] for obj in meshes}
        matrices = {obj: obj.matrix_world.copy() for obj in objects}
        width_info = {}
        if args.width_only:
            assert len(meshes) == 1
            obj = meshes[0]
            points = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
            obj.data.calc_loop_triangles()
            faces = np.array([t.vertices[:] for t in obj.data.loop_triangles])
            source_width = .58 if name == 'shirt' else section_width(points, faces, .98)
            # The A-pose arms also cross the waist plane: exclude them from torso width.
            torso_faces = body_faces[np.max(np.abs(body_vertices[body_faces,0]-waist.x),axis=1)<.30]
            target_width = abs(anchors['fit_shoulder_L'].translation.x - anchors['fit_shoulder_R'].translation.x) if name == 'shirt' else section_width(body_vertices, torso_faces, waist.z)
            if name == 'shirt':
                weights = smooth((np.abs(points[:, 0])-.18)/.11) * smooth((points[:, 2]-.65)/.20)
                # Continuous spatial weights also bridge duplicated vertices at UV seams.
                weights = np.maximum(weights, smooth((np.abs(points[:,0])-.29)/.05))
                dx = np.sign(points[:,0]) * (target_width-source_width)/2 * weights
            else:
                weights = smooth((points[:,2]-.88)/.10)
                dx = points[:,0] * (target_width/source_width-1) * weights
            adjusted = points.copy(); adjusted[:,0] += dx
            inverse = obj.matrix_world.inverted()
            for vertex, point in zip(obj.data.vertices, adjusted):
                vertex.co = inverse @ Vector(point)
            obj.data.update()
            actual = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
            assert np.max(np.abs(actual[:,1:]-points[:,1:])) < 1e-6
            assert np.max(np.abs(actual[weights==0]-points[weights==0])) < 1e-6
            width_info = {'source_width_cm':source_width*100, 'target_width_cm':target_width*100,
                          'maximum_horizontal_shift_cm':float(np.max(np.abs(dx))*100),
                          'depth_and_length_unchanged':True, 'unaffected_region_unchanged':True}
        delta = target - source
        for obj in objects:
            if obj.parent not in objects:
                obj.location += delta
        bpy.context.view_layer.update()
        for obj in meshes:
            if not args.width_only:
                assert original[obj] == [tuple(v.co) for v in obj.data.vertices]
            before, after = matrices[obj], obj.matrix_world
            assert all(abs(before[i][j] - after[i][j]) < 1e-6 for i in range(3) for j in range(3))
            assert (after.translation - before.translation - delta).length < 1e-6
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            obj.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(output/(name+'.glb')), export_format='GLB', use_selection=True)
        report['garments'][name] = {'source': path.name, 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'source_landmark_blender_m': list(source), 'target_landmark_blender_m': list(target),
            'translation_blender_m': list(delta), 'local_vertices_unchanged': not args.width_only, 'width_adjustment':width_info,
            'world_linear_transform_unchanged': True, 'vertices': sum(len(obj.data.vertices) for obj in meshes)}
    (output/'placement-report.json').write_text(json.dumps(report, indent=2)+'\n')
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'original-garments-placed.blend'), compress=True)
    print('PASS: '+report['mode']+'; length/depth preserved; collision skipped', flush=True)


def smooth(value):
    value = np.clip(value, 0, 1)
    return value*value*(3-2*value)


def section_width(vertices, faces, height):
    edges = np.unique(np.sort(np.vstack((faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]])), axis=1), axis=0)
    a, b = vertices[edges[:,0]], vertices[edges[:,1]]
    mask = (a[:,2]-height)*(b[:,2]-height)<0
    a,b = a[mask],b[mask]
    if not len(a):
        raise ValueError('Missing waist section')
    points = a+(b-a)*((height-a[:,2])/(b[:,2]-a[:,2]))[:,None]
    return float(np.ptp(points[:,0]))


if __name__ == '__main__':
    main()
