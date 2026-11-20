# 역할: DB 크기를 유지하면서 신체 랜드마크에 맞는 초기 의류 자세 후보를 만듭니다.
import math

import bpy
import bmesh
from mathutils import Matrix, Quaternion, Vector

from core.pose_geometry import neck_registration, angle_degrees, sleeve_target_on_arm


def smooth(value):
    value=max(0.,min(1.,value))
    return value*value*(3-2*value)


def anchor_positions(anchors):
    return {a['name']:Vector((a['translation'][0],-a['translation'][2],a['translation'][1])) for a in anchors}


def neck_opening(obj, coordinates):
    bm=bmesh.new(); bm.from_mesh(obj.data); bm.verts.ensure_lookup_table()
    graph={}
    for edge in bm.edges:
        if edge.is_boundary:
            a,b=(v.index for v in edge.verts)
            graph.setdefault(a,set()).add(b); graph.setdefault(b,set()).add(a)
    bm.free()
    if not graph or any(len(neighbors) != 2 for neighbors in graph.values()):
        raise ValueError('No closed neck opening for initial pose')
    loops=[]; remaining=set(graph)
    while remaining:
        todo=[remaining.pop()]; loop=[]
        while todo:
            vertex=todo.pop(); loop.append(vertex)
            for other in graph[vertex]:
                if other in remaining: remaining.remove(other); todo.append(other)
        loops.append(loop)
    collar=max(loops,key=lambda loop:sum(coordinates[i].z for i in loop)/len(loop))
    return {'L':max((coordinates[i] for i in collar),key=lambda p:p.x).copy(),
            'R':min((coordinates[i] for i in collar),key=lambda p:p.x).copy()}


def articulate(obj, coordinates, source, necks, body, mode):
    """Use Blender's volume-preserving Armature for initial pose, not scaling."""
    rig_data=bpy.data.armatures.new('FitMeInitialPose')
    rig=bpy.data.objects.new('FitMeInitialPose',rig_data); bpy.context.collection.objects.link(rig)
    groups=[]; modifier=None
    try:
        bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True)
        bpy.context.view_layer.objects.active=rig; bpy.ops.object.mode_set(mode='EDIT')
        root=rig_data.edit_bones.new('_FitMePoseRoot'); root.head=(0,0,-.4); root.tail=(0,0,0)
        for side in ('L','R'):
            shoulder=source['fit_shoulder_'+side]; cuff=source['fit_cuff_'+side]
            clav=rig_data.edit_bones.new('_FitMeClav_'+side); clav.head=necks[side]; clav.tail=shoulder; clav.parent=root
            arm=rig_data.edit_bones.new('_FitMeArm_'+side); arm.head=shoulder; arm.tail=cuff; arm.parent=clav
        bpy.ops.object.mode_set(mode='OBJECT')
        names=['_FitMePoseRoot',*[prefix+side for side in ('L','R') for prefix in ('_FitMeClav_','_FitMeArm_')]]
        weights={name:obj.vertex_groups.new(name=name) for name in names}; groups=list(weights.values())
        for index,point in enumerate(coordinates):
            side='L' if point.x >= 0 else 'R'; sign=1 if side == 'L' else -1
            shoulder=source['fit_shoulder_'+side]; cuff=source['fit_cuff_'+side]
            axis=(cuff-shoulder).normalized(); extent=(cuff-shoulder).length
            along=(point-shoulder).dot(axis); radial=((point-shoulder)-axis*along).length
            outward=smooth((sign*point.x-sign*necks[side].x)/max(.02,abs(shoulder.x-necks[side].x)))
            radius=.07+.06*(1-max(0.,min(1.,along/extent)))
            arm=outward*smooth(along/.04)*(1-smooth((radial-radius)/.04))
            clav=outward*smooth((point.z-shoulder.z+.12)/.12)*(1-arm)
            for name,value in [('_FitMeArm_'+side,arm),('_FitMeClav_'+side,clav),('_FitMePoseRoot',1-arm-clav)]:
                if value > 0: weights[name].add([index],value,'REPLACE')
        posed=dict(source)
        for side in ('L','R'):
            neck=necks[side]; shoulder=source['fit_shoulder_'+side]; cuff=source['fit_cuff_'+side]
            if mode == 'shoulders_and_sleeves':
                rotation=(shoulder-neck).rotation_difference(body['fit_shoulder_'+side]-body['fit_neck_'+side])
            else: rotation=Quaternion()
            if math.degrees(rotation.angle) > 35: raise ValueError('Shoulder pose difference exceeds 35 degrees')
            clav=Matrix.Translation(neck)@rotation.to_matrix().to_4x4()@Matrix.Translation(-neck)
            bone=rig.pose.bones['_FitMeClav_'+side]; bone.matrix=clav@bone.bone.matrix_local
            bpy.context.view_layer.update()
            new_shoulder=clav@shoulder
            target=Vector(sleeve_target_on_arm(new_shoulder,new_shoulder+(cuff-shoulder),
                body['fit_shoulder_'+side],body['fit_wrist_'+side]))
            arm_rotation=(cuff-shoulder).rotation_difference(target-new_shoulder)
            if math.degrees(arm_rotation.angle) > 35: raise ValueError('Sleeve pose difference exceeds 35 degrees')
            arm=Matrix.Translation(new_shoulder)@arm_rotation.to_matrix().to_4x4()@Matrix.Translation(-shoulder)
            bone=rig.pose.bones['_FitMeArm_'+side]; bone.matrix=arm@bone.bone.matrix_local
            bpy.context.view_layer.update()
            posed['fit_shoulder_'+side]=new_shoulder; posed['fit_cuff_'+side]=arm@cuff
        obj.data.vertices.foreach_set('co',[value for point in coordinates for value in point]); obj.data.update()
        modifier=obj.modifiers.new('Initial garment pose','ARMATURE'); modifier.object=rig
        modifier.use_deform_preserve_volume=True
        bpy.context.view_layer.update()
        evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        return [v.co.copy() for v in evaluated.data.vertices],posed
    finally:
        if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
        if modifier: obj.modifiers.remove(modifier)
        for group in groups: obj.vertex_groups.remove(group)
        bpy.data.objects.remove(rig,do_unlink=True)
        if rig_data.users == 0: bpy.data.armatures.remove(rig_data)
        bpy.context.view_layer.objects.active=obj


def candidates(obj, coordinates, anchors, body, observed_slope=None):
    source=anchor_positions(anchors)
    for side in ('L','R'):
        for tag in ('shoulder','wrist'):
            if 'fit_'+tag+'_'+side not in body: raise ValueError('Missing body arm landmarks')
    necks=neck_opening(obj,coordinates)
    body=dict(body); neck_source='sam_projected_neck_landmarks'
    if any('fit_neck_'+side not in body for side in ('L','R')):
        if type(observed_slope) not in (int,float) or not math.isfinite(observed_slope) or not -10 <= observed_slope <= 45:
            raise ValueError('Missing body neck landmarks and measured shoulder slope')
        neck_source='measured_shoulder_slope_fallback'
        for side,sign in (('L',1),('R',-1)):
            body['fit_neck_'+side]=body['fit_shoulder_'+side]+Vector((-sign*.10,0,.10*math.tan(math.radians(observed_slope))))
    shift=Vector(neck_registration(necks,{s:body['fit_neck_'+s] for s in ('L','R')},
                                   {s:body['fit_shoulder_'+s] for s in ('L','R')}))
    diagnostics={'neck_source':neck_source,'registration_translation_m':list(shift),'sides':{}}
    for side in ('L','R'):
        diagnostics['sides'][side]={
            'sleeve_axis_difference_degrees':angle_degrees(source['fit_cuff_'+side]-source['fit_shoulder_'+side],
                body['fit_wrist_'+side]-body['fit_shoulder_'+side]),
            'shoulder_axis_difference_degrees':angle_degrees(source['fit_shoulder_'+side]-necks[side],
                body['fit_shoulder_'+side]-body['fit_neck_'+side]),
            'body_shoulder_m':list(body['fit_shoulder_'+side]),'garment_shoulder_m':list(source['fit_shoulder_'+side])}
    translated=[p+shift for p in coordinates]
    moved={name:(point+shift if name != 'fit_anchor' else point) for name,point in source.items()}
    yield translated,moved,{**diagnostics,'mode':'neck_registration'}
    moved_necks={side:point+shift for side,point in necks.items()}
    for mode in ('sleeves','shoulders_and_sleeves'):
        try:
            posed,landmarks=articulate(obj,translated,moved,moved_necks,body,mode)
            yield posed,landmarks,{**diagnostics,'mode':mode}
        except ValueError as exc:
            yield coordinates,source,{**diagnostics,'mode':mode,'rejected':str(exc)}
