# 역할: 실제 SAM 신체로 의류 크기를 조절하고 Cloth 충돌 안정화 결과를 확정합니다.
"""Resize the template to the actual SAM, then validate Cloth collision relaxation."""
import base64
import math
from hashlib import sha256
from pathlib import Path
import tempfile
import time
import bmesh

import bpy
from mathutils import Matrix, Vector

from core.cloth_contract import FRAMES, MAX_BODY_BYTES, SOFT_BUDGET_SECONDS, validate_simulation, stop_reason, mass_settings
from core.cloth_geometry import inside_region
from geometry.collision_proxy import build_proxy
from geometry.sam_sizing import resize_to_sam
from geometry.mesh_validation import BodySurface, validate_mesh
from core.pose_geometry import orient_closed_surface
from geometry.cloth_self_collision import configure_self_collision


def stage(name, **values):
    import json
    print('FITME_STAGE '+json.dumps({'stage':name,**values}),flush=True)


def penetration(points, edges, polygons, tree):
    samples = list(points)
    samples.extend((points[a]+points[b])*.5 for a,b in edges)
    samples.extend(sum((points[i] for i in face),Vector())/len(face) for face in polygons)
    depth, inside = 0., 0
    for point in samples:
        nearest, normal, _, distance = tree.find_nearest(point)
        if nearest is None:
            raise ValueError('Could not validate cloth collision')
        if (point-nearest).dot(normal) < 0 and distance > .001:
            inside += 1
            depth = max(depth,distance)
    exact=tree.intersections(points,polygons)
    tree.last_intersections=exact
    if not exact['validation_complete']:
        stage('body_validation_incomplete',**exact)
        tree.validation_incomplete=True
    return depth, inside+exact['crossing_pairs']+int(not exact['validation_complete'])


def contact_diagnostics(points,edges,polygons,tree,body):
    samples=list(points)
    samples.extend((points[a]+points[b])*.5 for a,b in edges)
    samples.extend(sum((points[i] for i in face),Vector())/len(face) for face in polygons)
    shoulder_z=sum(body['fit_shoulder_'+side].z for side in ('L','R'))/2 if all(
        'fit_shoulder_'+side in body for side in ('L','R')) else max(p.z for p in points)
    shoulder_x=max((abs(body['fit_shoulder_'+side].x) for side in ('L','R')
                    if 'fit_shoulder_'+side in body),default=.18)
    hem=min(p.z for p in points)+.08
    regions={}; depth=0.; inside=0; deepest=None
    for point in samples:
        nearest,normal,_,distance=tree.find_nearest(point)
        if nearest is None: raise ValueError('No SAM contact for placement diagnostics')
        if (point-nearest).dot(normal) >= 0 or distance <= .001: continue
        inside+=1
        if distance > depth: depth=distance; deepest=list(point)
        if point.z > shoulder_z-.10: region='shoulder_neck'
        elif abs(point.x) > shoulder_x*.8 and point.z > shoulder_z-.40:
            region='sleeve_L' if point.x >= 0 else 'sleeve_R'
        elif point.z < hem: region='hem'
        else: region='torso_front' if point.y < 0 else 'torso_back'
        entry=regions.setdefault(region,{'inside_samples':0,'depth_m':0.})
        entry['inside_samples']+=1; entry['depth_m']=max(entry['depth_m'],distance)
    return {'depth_m':depth,'inside_samples':inside,'sample_count':len(samples),
            'inside_fraction':inside/max(1,len(samples)),'deepest_point_m':deepest,'regions':regions}


def support_group(obj, rest, kind, anchors):
    existing = obj.vertex_groups.get('FitMeSupport')
    if existing is not None:
        if not any(any(g.group == existing.index and g.weight > 0 for g in v.groups)
                   for v in obj.data.vertices):
            raise ValueError('Empty explicit FitMeSupport group')
        return existing
    # Find actual opening loops, rather than pinning a rectangular torso band.
    bm = bmesh.new(); bm.from_mesh(obj.data); bm.verts.ensure_lookup_table()
    adjacency = {}
    for edge in bm.edges:
        if len(edge.link_faces) > 2:
            bm.free(); raise ValueError('Non-manifold cloth edge')
        if edge.is_boundary:
            a,b = (v.index for v in edge.verts)
            adjacency.setdefault(a,set()).add(b); adjacency.setdefault(b,set()).add(a)
    bm.free()
    if not adjacency or any(len(neighbors) != 2 for neighbors in adjacency.values()):
        raise ValueError('Cloth openings must be closed boundary loops')
    loops = []
    unseen = set(adjacency)
    while unseen:
        todo = [unseen.pop()]; loop = []
        while todo:
            vertex = todo.pop(); loop.append(vertex)
            for neighbor in adjacency[vertex]:
                if neighbor in unseen:
                    unseen.remove(neighbor); todo.append(neighbor)
        loops.append(loop)
    opening = max(loops,key=lambda loop:sum(rest[i].z for i in loop)/len(loop))
    group = obj.vertex_groups.new(name='FitMeSupport')
    group.add(opening, .6 if kind == 'crewneck' else 1., 'REPLACE')
    if kind == 'crewneck':
        for side in ('L','R'):
            x,y,z = next(a for a in anchors if a['name'] == 'fit_shoulder_'+side)['translation']
            target = Vector((x,-z,y))
            closest = min(range(len(rest)), key=lambda i:(rest[i]-target).length_squared)
            group.add([closest],1.,'REPLACE')
    return group


def simulate(obj, anchors, kind, encoded_body, model_id, checkpoint=None):
    started = time.monotonic()
    stage('body_import_start')
    body = base64.b64decode(encoded_body, validate=True)
    if len(body) > MAX_BODY_BYTES or sha256(body).hexdigest() != model_id:
        raise ValueError('Collision model hash mismatch')
    before = set(bpy.data.objects)
    with tempfile.TemporaryDirectory(prefix='fitme-cloth-') as folder:
        path = Path(folder)/'body.glb'
        path.write_bytes(body)
        bpy.ops.import_scene.gltf(filepath=str(path))
    imported = set(bpy.data.objects)-before
    name = 'fit_anchor_waist' if kind == 'slacks' else 'fit_anchor'
    targets = [item for item in imported if item.name == name or item.name.startswith(name+'.')]
    if len(targets) != 1:
        raise ValueError('Missing unique body collision anchor')
    bpy.context.view_layer.update()
    source = next(a for a in anchors if a['name'] == name)['translation']
    x,y,z = source
    alignment = Matrix.Translation((x,-z,y)) @ targets[0].matrix_world.inverted()
    body_landmarks={}
    for label in ('fit_anchor_waist','fit_shoulder_L','fit_shoulder_R','fit_wrist_L','fit_wrist_R','fit_neck_L','fit_neck_R'):
        nodes=[item for item in imported if item.name == label or item.name.startswith(label+'.')]
        if len(nodes) == 1: body_landmarks[label]=alignment@nodes[0].matrix_world.translation
    import json, struct
    json_size=struct.unpack_from('<I',body,12)[0]
    document=json.loads(body[20:20+json_size])
    measurements=document['scenes'][document.get('scene',0)].get('extras',{}).get('fitme_measurements',{})
    vertices, faces = [], []
    for item in imported:
        if item.type != 'MESH':
            continue
        if item.modifiers or item.data.shape_keys:
            raise ValueError('Collision avatar must be a static exported mesh')
        transform = alignment @ item.matrix_world
        offset = len(vertices)
        vertices.extend(transform @ vertex.co for vertex in item.data.vertices)
        faces.extend(tuple(offset+i for i in face.vertices) for face in item.data.polygons)
    if not vertices or not faces:
        raise ValueError('No body collision surface')
    faces,normal_report=orient_closed_surface(vertices,faces)
    stage('body_collision_geometry',vertices=len(vertices),faces=len(faces),
          height_m=max(p.z for p in vertices)-min(p.z for p in vertices),**normal_report)
    for item in imported:
        bpy.data.objects.remove(item, do_unlink=True)

    stage('sam_sizing_start',catalog_measurements_used=False)
    try:
        sizing=resize_to_sam(obj,anchors,kind,vertices,faces,body_landmarks,measurements)
    except ValueError as exc:
        report={'status':'failed','failure_reasons':['sam_sizing_failed'],'frames':0,
                'method':'sam_body_cloth_collision','body_model_id':model_id,
                'body_sizing':{'catalog_measurements_used':False,'error':str(exc)}}
        if checkpoint: checkpoint([v.co.copy() for v in obj.data.vertices],report)
        return report
    stage('sam_sizing_complete',**sizing)
    rest = [v.co.copy() for v in obj.data.vertices]
    reference=[p.copy() for p in rest]
    edges = [tuple(e.vertices) for e in obj.data.edges]
    polygons = [tuple(face.vertices) for face in obj.data.polygons]
    rest_lengths = [(rest[a]-rest[b]).length for a,b in edges]
    mass=mass_settings(kind,len(rest))
    stage('cloth_mass_configuration',**mass)
    tree = BodySurface(vertices,faces)
    collider,proxy_report,collision_bounds=build_proxy(vertices,faces,rest)
    stage('collision_proxy_ready',**proxy_report)
    initial_depth,initial_inside=penetration(rest,edges,polygons,tree)
    initial_quality=validate_mesh(rest,polygons)
    base_report={'frames':0,'method':'sam_body_cloth_collision','rest_shape':'sam_sized_template',
                 'body_model_id':model_id,'body_sizing':sizing,
                 'initial_penetration_m':initial_depth,'initial_intersection_samples':initial_inside,
                 'initial_triangle_intersections':tree.last_intersections,
                 'preset':'sam_collision_relaxation_v1','self_collision_enabled':True,
                 'mass':mass,'collision_proxy':proxy_report,'spring_reference':'sam_sized_template',
                 'initial_mesh_quality':initial_quality,'body_surface':normal_report,
                 'gravity_mode':'collision_relaxation_zero_gravity',
                 'collision_check':'samples_and_full_body_triangle_crossings'}
    stage('initial_contact',depth_m=initial_depth,inside_samples=initial_inside,
          seconds=time.monotonic()-started,rest_shape='sam_sized_template')
    if not initial_quality['valid']:
        report={**base_report,'status':'failed','failure_reasons':['invalid_cloth_mesh']}
        if checkpoint: checkpoint(rest,report)
        bpy.data.objects.remove(collider,do_unlink=True)
        return report
    sam_rest=reference
    pin = support_group(obj,rest,kind,anchors)
    # An embedded pinned shoulder cannot leave the body, even with collision
    # enabled. Release only embedded supports; safe supports stay attached.
    released=[]
    for index,point in enumerate(rest):
        if not any(g.group == pin.index and g.weight > 0 for g in obj.data.vertices[index].groups): continue
        surface,normal,_,_=tree.find_nearest(point)
        if surface is not None and (point-surface).dot(normal) < .004: released.append(index)
    if released: pin.remove(released)
    base_report['released_embedded_supports']=len(released)
    stage('cloth_recovery_start',initial_overlap=bool(initial_inside),released_supports=len(released))
    # SAM sizing is intentional. Only subsequent Cloth deformation is checked
    # against the new SAM-sized rest shape; catalog sizes are not spring targets.
    obj.shape_key_add(name='Basis',from_mix=False)
    rest_key=obj.shape_key_add(name='FitMeSAMRest',from_mix=False)
    rest_key.data.foreach_set('co',[v for point in sam_rest for v in point]); rest_key.value=0.
    cloth = obj.modifiers.new('SAM-sized cloth', 'CLOTH')
    settings = cloth.settings
    settings.rest_shape_key=rest_key
    settings.quality = 8
    settings.mass = mass['vertex_mass_kg']
    mass['applied_vertex_mass_kg']=float(settings.mass)
    mass['applied_total_mass_kg']=float(settings.mass)*len(rest)
    stage('cloth_mass_applied',**mass)
    settings.tension_stiffness = 500
    settings.compression_stiffness = 500
    settings.shear_stiffness = 500
    settings.tension_damping = 10
    settings.compression_damping = 10
    settings.shear_damping = 10
    settings.time_scale = .5
    settings.bending_stiffness = .5
    settings.vertex_group_mass = pin.name
    settings.pin_stiffness = 1.
    settings.shrink_min = 0.
    settings.use_sewing_springs = False
    settings.use_pressure = False
    cloth.collision_settings.use_collision = True
    cloth.collision_settings.distance_min = .003
    cloth.collision_settings.collision_quality = 3
    resolution=configure_self_collision(obj,sam_rest,edges,polygons,cloth.collision_settings,reference_name='sam_sized_template')
    base_report['self_collision_resolution']=resolution
    base_report['self_collision_enabled']=bool(resolution['configured'])
    stage('self_collision_resolution',**resolution)
    if not resolution['configured']:
        obj.modifiers.remove(cloth)
        report={**base_report,'status':'failed','failure_reasons':['self_collision_setup_failed'],
                'stop_reason':resolution['reason']}
        if checkpoint: checkpoint(rest,report)
        bpy.data.objects.remove(collider,do_unlink=True)
        return report
    frame_limit=min(FRAMES,36)
    cloth.point_cache.frame_start = 1
    cloth.point_cache.frame_end = frame_limit
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, frame_limit
    scene.render.fps = 24
    scene.gravity = (0,0,0)
    previous = rest
    current = rest
    stable = 0
    final_frame = 0
    ended = 'frame_limit'
    report = {**base_report,'status':'failed','failure_reasons':['simulation_incomplete']}
    if checkpoint: checkpoint(rest,report)
    for frame in range(1, frame_limit+1):
        if time.monotonic()-started >= SOFT_BUDGET_SECONDS:
            ended = 'simulation_timeout'; break
        frame_started = time.monotonic()
        stage('cloth_frame_start',frame=frame)
        scene.frame_set(frame)
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        candidate = [v.co.copy() for v in evaluated.data.vertices]
        stage('cloth_frame_complete',frame=frame,seconds=time.monotonic()-frame_started)
        if len(candidate) != len(rest):
            ended = 'simulation_diverged'; break
        if any(not math.isfinite(value) for point in candidate for value in point):
            ended = 'non_finite_simulation'; break
        lengths = [(candidate[a]-candidate[b]).length for a,b in edges]
        if any(length <= 0 for length in lengths):
            ended = 'simulation_diverged'; break
        previous,current = current,candidate
        final_frame = frame
        movement = max((a-b).length for a,b in zip(current,previous))
        stable = stable+1 if movement < .001 else 0
        stretch = max(b/a for a,b in zip(rest_lengths,lengths))
        ended = stop_reason(frame,stable,time.monotonic()-started,stretch)
        if not inside_region(current,collision_bounds): ended='collision_region_exited'
        stage('cloth_frame',frame=frame,seconds=time.monotonic()-frame_started,
              elapsed_seconds=time.monotonic()-started,movement_m=movement,max_stretch=stretch)
        if checkpoint and (frame == 1 or frame % 4 == 0 or ended):
            depth,_ = penetration(current,edges,polygons,tree)
            report = {**base_report,**validate_simulation(rest_lengths,lengths,movement,depth),
                      'frames':frame,'status':'failed','failure_reasons':['simulation_incomplete']}
            checkpoint(current,report)
        if ended: break
    movement = max((a-b).length for a,b in zip(current, previous))
    depth,remaining_inside = penetration(current,edges,polygons,tree)
    report = validate_simulation(rest_lengths,
        [(current[a]-current[b]).length for a,b in edges], movement, depth,
        stable_frames=stable, mesh_quality=validate_mesh(current,polygons,reference),
        body_intersections=tree.intersections(current,polygons))
    report['final_intersection_count']=remaining_inside
    if remaining_inside:
        report['status']='failed'
        if 'body_penetration' not in report['failure_reasons']: report['failure_reasons'].append('body_penetration')
    if ended not in (None,'settled','frame_limit'):
        report['status'] = 'failed'
        report['failure_reasons'].append(ended)
    obj.modifiers.clear()
    obj.shape_key_clear()
    obj.data.vertices.foreach_set('co',[v for point in current for v in point])
    obj.data.update()
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(obj.data); bm.free()
    bpy.data.objects.remove(collider, do_unlink=True)
    return {**base_report,**report,'frames':final_frame,'stop_reason':ended or 'frame_limit',
            'self_collision_enabled':True,'elapsed_seconds':time.monotonic()-started}
