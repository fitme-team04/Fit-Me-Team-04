# 역할: 상품 실측을 사용하지 않고 실제 SAM 표면·팔 자세로 의류 원형의 크기를 맞춥니다.
import math

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from core.sam_sizing import bounded_radial_ratio
from core.arm_profiles import radial_basis, ellipse_section, offset_radial_profile, sample_radial_profiles
from core.mesh_quality import triangulate, triangle_intersection
from core.body_sections import torso_contour, arm_contour
from geometry.garment_pose import anchor_positions, neck_opening


def _smooth(value):
    value=np.clip(value,0.,1.)
    return value*value*(3.-2.*value)


def _axis(start,end,label):
    start=np.asarray(start,dtype=float);end=np.asarray(end,dtype=float)
    if start.shape!=(3,) or end.shape!=(3,) or not np.isfinite([start,end]).all():
        raise ValueError('Invalid '+label+' landmarks')
    vector=end-start;extent=float(np.linalg.norm(vector))
    if not math.isfinite(extent) or extent<1e-6:raise ValueError('Degenerate '+label+' axis')
    return start,vector/extent,extent


def _set_points(obj,points):
    points=np.asarray(points,dtype=float)
    if points.shape!=(len(obj.data.vertices),3) or not np.isfinite(points).all():
        raise ValueError('Non-finite SAM-sized garment')
    obj.data.vertices.foreach_set('co',points.ravel());obj.data.update()


def _arm_weights(points, source, necks):
    weights={}
    for side,sign in (('L',1),('R',-1)):
        start=np.asarray(source['fit_shoulder_'+side]); end=np.asarray(source['fit_cuff_'+side])
        start,axis,extent=_axis(start,end,'template sleeve')
        along=(points-start)@axis; radial=np.linalg.norm(points-start-along[:,None]*axis,axis=1)
        outward=_smooth((sign*points[:,0]-sign*necks[side].x)/max(.02,abs(start[0]-necks[side].x)))
        radius=.07+.06*(1-np.clip(along/extent,0,1))
        # Blend over a shoulder joint rather than switching fields in 6 cm.
        weights[side]=outward*_smooth((along+.06)/.12)*(1-_smooth((radial-radius)/.04))
    return weights


def _profiles(points, levels, mask, *, clearance=0., enclosing=False, triangles=None):
    selected=points[mask]
    if len(selected)<8: raise ValueError('Insufficient SAM sizing surface samples')
    values=[]
    for z in levels:
        if triangles is not None:
            try:row=torso_contour(points,triangles,float(z))
            except ValueError:
                values.append(None);continue
        else:
            distances=np.abs(selected[:,2]-z)
            row=selected[distances<.018]
            if len(row)<8: row=selected[np.argsort(distances)[:min(40,len(selected))]]
        lo=row[:,:2].min(0); hi=row[:,:2].max(0); center=(lo+hi)/2
        radii=np.maximum((hi-lo)/2,.008)+clearance
        if enclosing:
            radius=np.sqrt(np.sum(((row[:,:2]-center)/radii)**2,axis=1)).max()
            radii*=max(1.,radius)
        values.append((*center,*radii))
    valid=[i for i,value in enumerate(values) if value is not None]
    if not valid:raise ValueError('No isolated SAM torso sizing contours')
    if len(valid)!=len(values):
        # Below the crotch there are two leg contours; carry the last valid hip
        # envelope through the shirt hem instead of measuring arms or both legs.
        known=np.asarray([values[i] for i in valid]);knots=np.asarray(levels)[valid]
        return np.column_stack([np.interp(levels,knots,known[:,k]) for k in range(4)])
    return np.asarray(values)


def _at(level, levels, profile):
    return np.column_stack([np.interp(level,levels,profile[:,i]) for i in range(profile.shape[1])])


def _radial_girth_cm(radii):
    angles=np.arange(len(radii))*2*np.pi/len(radii)
    points=np.column_stack((np.cos(angles),np.sin(angles)))*radii[:,None]
    return float(np.linalg.norm(points-np.roll(points,1,axis=0),axis=1).sum()*100)


def _measurement_height(measurements, key, bottom, fallback):
    entry=measurements.get(key,{})
    value=entry.get('measured') if isinstance(entry,dict) else entry
    return bottom+float(value)/100 if type(value) in (int,float) and math.isfinite(value) else fallback


def _arm_profile(points,triangles,start,axis,length,basis,levels,radius_limit,clearance):
    """Trace isolated wrist-to-shoulder sections; never turn an axis offset into thickness."""
    rows={};previous_area=None;rejected=[];girths={}
    for index in range(len(levels)-1,-1,-1):
        origin=start+axis*(float(levels[index])*length)
        try:
            contour=arm_contour(points,triangles,origin,axis,max_radius=radius_limit)
            section=(offset_radial_profile(contour,origin,axis,basis=basis,clearance_m=clearance)
                     if clearance else ellipse_section(contour,origin,axis,basis=basis))
            # A sudden proximal area jump is generally the arm merging into
            # the torso. Continue the last independent arm instead of sizing
            # the sleeve from the entire shoulder/chest contour.
            if previous_area is not None and not .35*previous_area<=section['area_m2']<=2*previous_area:
                raise ValueError('Arm section merged with shoulder or torso')
            rows[index]=np.r_[section['offset'],section['radii'],section.get('angles_radii',[])]
            girths[index]=section['perimeter_m'];previous_area=section['area_m2']
        except ValueError:
            rejected.append(index)
            if rows and levels[index]<.35:
                rejected.extend(range(index));break
    valid=sorted(rows)
    if len(valid)<4:raise ValueError('Insufficient isolated arm sections for sleeve sizing')
    knots=np.asarray(levels)[valid];known=np.asarray([rows[i] for i in valid])
    profile=np.column_stack([np.interp(levels,knots,known[:,k]) for k in range(known.shape[1])])
    report={'valid_sections':len(valid),'rejected_sections':len(rejected),
            'valid_progress_range':[float(knots[0]),float(knots[-1])],
            'clearance_m':clearance,'section_center':'polygon_area_centroid',
            'contour_model':'convex_offset_radial' if clearance else 'source_ellipse_coordinates',
            'measured_girth_range_cm':[float(min(girths.values())*100),float(max(girths.values())*100)]}
    return profile,report


def _validate_sleeves(obj,fields):
    """A collision-free but oversized sleeve is still a sizing error."""
    points=np.asarray([v.co[:] for v in obj.data.vertices])
    faces=np.asarray(triangulate([tuple(p.vertices) for p in obj.data.polygons]),dtype=int)
    reports={}
    for side,field in fields.items():
        start,axis,length,basis,levels,profile=field;rows=[]
        for progress in (.4,.55,.75,.9):
            origin=start+axis*(progress*length);expected=_at(np.asarray([progress]),levels,profile)[0]
            loop=arm_contour(points,faces,origin,axis,max_radius=.25)
            measured=ellipse_section(loop,origin,axis,basis=basis)
            center=origin+basis@expected[:2]
            center_gap=float(np.linalg.norm(measured['center']-center))
            expected_girth=_radial_girth_cm(expected[4:])/100
            girth_error=measured['perimeter_m']-expected_girth
            rows.append({'progress':progress,'girth_cm':measured['perimeter_m']*100,
                         'target_girth_cm':expected_girth*100,'center_gap_mm':center_gap*1000})
            if center_gap>.010 or girth_error>.020 or girth_error<-.030:
                raise ValueError('Sleeve '+side+' departs from the SAM arm section at '+str(progress))
        reports[side]={'valid':True,'sections':rows,'max_center_gap_m':.010,
                       'max_girth_excess_over_profile_m':.020}
    return reports


def resize_to_sam(obj, anchors, kind, body_vertices, body_faces, body_landmarks, measurements):
    """Set a new SAM-sized rest shape; never treat catalog sizes as fit inputs."""
    original=np.asarray([v.co[:] for v in obj.data.vertices],dtype=float)
    body=np.asarray(body_vertices,dtype=float)
    if not np.isfinite(original).all() or not np.isfinite(body).all():
        raise ValueError('Non-finite SAM sizing surface')
    if kind!='crewneck':
        return _resize_lower_body(obj,anchors,body,body_vertices,body_faces,body_landmarks,measurements)
    source=anchor_positions(anchors)
    necks=neck_opening(obj,[Vector(p) for p in original])
    required=[f'fit_{tag}_{side}' for side in ('L','R') for tag in ('shoulder','wrist','neck')]
    if any(key not in body_landmarks for key in required): raise ValueError('Missing SAM sizing landmarks')
    old_top=float(np.mean([p.z for p in necks.values()]))
    new_top=float(np.mean([body_landmarks['fit_neck_'+side].z for side in ('L','R')]))
    old_bottom=float(original[:,2].min()); bottom=float(body[:,2].min()); height=float(np.ptp(body[:,2]))
    hip=_measurement_height(measurements,'hip_line_height_cm',bottom,bottom+height*.49)
    new_bottom=hip-.04
    if old_top-old_bottom<.1 or new_top-new_bottom<.1: raise ValueError('Invalid SAM torso length')
    scale=(new_top-new_bottom)/(old_top-old_bottom)
    target_z=new_top+(original[:,2]-old_top)*scale
    weights=_arm_weights(original,source,necks)
    trunk_weight=1-np.maximum(weights['L'],weights['R'])
    levels=np.linspace(old_bottom,old_top,48)
    old_profile=_profiles(original,levels,trunk_weight>.8)
    body_levels=new_top+(levels-old_top)*scale
    new_profile=_profiles(body,body_levels,np.ones(len(body),dtype=bool),clearance=.020,enclosing=True,
                          triangles=np.asarray(triangulate(body_faces),dtype=int))
    old=_at(original[:,2],levels,old_profile); new=_at(target_z,body_levels,new_profile)
    radial=(original[:,:2]-old[:,:2])/old[:,2:]
    radii=np.linalg.norm(radial,axis=1)
    if np.any(radii<1e-6): raise ValueError('Garment torso crosses sizing centerline')
    adjusted=np.asarray([bounded_radial_ratio(1.02+.1*(float(r)-1),amplitude=.1) for r in radii])
    torso=np.column_stack((new[:,:2]+radial/radii[:,None]*new[:,2:]*adjusted[:,None],target_z))
    posed=torso*trunk_weight[:,None]
    sleeve_reports={};cuff_centers={};sleeve_fields={}
    source_triangles=np.asarray(triangulate([tuple(p.vertices) for p in obj.data.polygons]),dtype=int)
    body_triangles=np.asarray(triangulate(body_faces),dtype=int)
    shoulder_width=abs(body_landmarks['fit_shoulder_L'].x-body_landmarks['fit_shoulder_R'].x)
    source_width=abs(source['fit_shoulder_L'].x-source['fit_shoulder_R'].x)
    for side,sign in (('L',1),('R',-1)):
        start=np.asarray(source['fit_shoulder_'+side]); end=np.asarray(source['fit_cuff_'+side]); axis=end-start
        start,axis,old_length=_axis(start,end,'template sleeve')
        target=np.asarray(body_landmarks['fit_shoulder_'+side]); target_end=np.asarray(body_landmarks['fit_wrist_'+side])
        target,body_axis,body_length=_axis(target,target_end,'SAM arm')
        target_end=target+body_axis*body_length*.94
        along=(original-start)@axis; radial=original-start-along[:,None]*axis
        progress=along/old_length;levels_arm=np.linspace(.04,.98,32)
        source_basis=radial_basis(axis);body_basis=radial_basis(body_axis)
        old_arm,old_diagnostics=_arm_profile(original,source_triangles,start,axis,old_length,
                    source_basis,levels_arm,max(.08,source_width*.5),0.)
        new_arm,diagnostics=_arm_profile(body,body_triangles,target,body_axis,body_length*.94,
                    body_basis,levels_arm,max(.06,shoulder_width*.4),.010)
        old_values=_at(progress,levels_arm,old_arm);new_values=_at(progress,levels_arm,new_arm)
        local=radial@source_basis-old_values[:,:2]
        normalized=local/old_values[:,2:];lengths=np.linalg.norm(normalized,axis=1)
        unit=local/np.maximum(np.linalg.norm(local,axis=1)[:,None],1e-9)
        adjustment=np.asarray([bounded_radial_ratio(1.+.1*(float(r)-1),amplitude=.05) for r in lengths])
        target_radius=sample_radial_profiles(new_values[:,4:],np.arctan2(unit[:,1],unit[:,0]))
        radial_target=new_values[:,:2]+unit*(target_radius*adjustment)[:,None]
        arm=target+progress[:,None]*(target_end-target)+radial_target@body_basis.T
        posed+=arm*weights[side][:,None]
        cuff_offset=_at(np.asarray([1.]),levels_arm,new_arm)[0,:2]
        cuff_centers['fit_cuff_'+side]=Vector(target_end+body_basis@cuff_offset)
        sleeve_fields[side]=(target,body_axis,body_length*.94,body_basis,levels_arm,new_arm)
        sample_u=np.asarray([.15,.3,.5,.7,.9]);sample_values=_at(sample_u,levels_arm,new_arm)
        sleeve_reports[side]={'body_arm_length_m':float(body_length),
            'garment_arm_length_m':float(np.linalg.norm(target_end-target)),
            'method':'isolated_arm_offset_contour','body_profile':diagnostics,'source_profile':old_diagnostics,
            'sections':[{'progress':float(u),'center_offset_mm':(values[:2]*1000).tolist(),
                         'enclosing_radii_mm':(values[2:4]*1000).tolist(),
                         'target_profile_girth_cm':_radial_girth_cm(values[4:])}
                         for u,values in zip(sample_u,sample_values)]}
    # The convex blend can enter the shoulder/underarm. Blender's outside-only
    # shrinkwrap corrects these local contacts before defining the spring rest.
    _set_points(obj,posed)
    contact={'trigger_m':.009,'offset_m':.010}
    _outside(obj,body_vertices,body_faces,**contact)
    fold_repair=_relax_folds(obj,body_vertices,body_faces,**contact)
    conditioning=_condition_cloth_mesh(obj)
    _outside(obj,body_vertices,body_faces,**contact)
    final_folds=_relax_folds(obj,body_vertices,body_faces,**contact)
    sleeve_validation=_validate_sleeves(obj,sleeve_fields)
    for anchor in anchors:
        name=anchor['name']
        if name in ('fit_anchor','fit_anchor_waist'): continue
        key=name.replace('fit_cuff_','fit_wrist_')
        if key in body_landmarks:
            p=body_landmarks[key].copy()
            if 'cuff' in name:p=cuff_centers[name]
            anchor['translation']=[p.x,p.z,-p.y]
    return {'method':'sam_surface_profiles_and_native_shrinkwrap','size_source':'sam_surface',
            'catalog_measurements_used':False,'clearance_m':.020,'spring_reference':'sam_sized_template',
            'torso_length_m':float(new_top-new_bottom),'sleeves':sleeve_reports,'fold_relaxation':fold_repair,
            'cloth_conditioning':conditioning,'final_fold_relaxation':final_folds,
            'sleeve_fit_validation':sleeve_validation,
            'sleeve_clearance_m':.010,'clearance_scope':'torso_profile',
            'contact_guard_trigger_m':.009,'contact_guard_offset_m':.010}


def _outside(obj,vertices,faces,*,trigger_m=.016,offset_m=.020):
    tree=BVHTree.FromPolygons(vertices,faces,all_triangles=False)
    contacts=[]
    for vertex in obj.data.vertices:
        nearest,normal,_,_=tree.find_nearest(vertex.co)
        if nearest is None:raise ValueError('Missing SAM clearance surface')
        if (vertex.co-nearest).dot(normal)<trigger_m:contacts.append(vertex.index)
    if not contacts:return
    mesh=bpy.data.meshes.new('FitMeSizingSurface');mesh.from_pydata(vertices,[],faces);mesh.update()
    target=bpy.data.objects.new('FitMeSizingSurface',mesh);bpy.context.collection.objects.link(target)
    modifier=None;group=obj.vertex_groups.new(name='FitMeSizingContact')
    try:
        group.add(contacts,1.,'REPLACE')
        modifier=obj.modifiers.new('SAM outside placement','SHRINKWRAP');modifier.target=target
        modifier.vertex_group=group.name
        modifier.wrap_method='NEAREST_SURFACEPOINT';modifier.wrap_mode='OUTSIDE_SURFACE';modifier.offset=offset_m
        bpy.context.view_layer.update()
        evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        points=[v.co.copy() for v in evaluated.data.vertices]
        obj.modifiers.remove(modifier);modifier=None
        _set_points(obj,points)
    finally:
        if modifier:obj.modifiers.remove(modifier)
        obj.vertex_groups.remove(group)
        bpy.data.objects.remove(target,do_unlink=True)
        if mesh.users==0:bpy.data.meshes.remove(mesh)


def _condition_cloth_mesh(obj):
    """Keep garment UV/materials while removing ill-conditioned micro triangles."""
    before=len(obj.data.vertices);faces=[tuple(p.vertices) for p in obj.data.polygons]
    if len(faces)<=2500:return {'applied':False,'vertices':before,'triangles':len(faces)}
    original=[v.co.copy() for v in obj.data.vertices]
    old_tree=BVHTree.FromPolygons(original,faces,all_triangles=False)
    modifier=obj.modifiers.new('SAM cloth mesh conditioning','DECIMATE')
    modifier.ratio=.2;modifier.use_collapse_triangulate=True
    reduced=None
    try:
        depsgraph=bpy.context.evaluated_depsgraph_get();depsgraph.update()
        reduced=bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph),depsgraph=depsgraph,
                                               preserve_all_data_layers=True)
    finally:obj.modifiers.remove(modifier)
    points=[v.co.copy() for v in reduced.vertices]
    polygons=[tuple(p.vertices) for p in reduced.polygons]
    tree=BVHTree.FromPolygons(points,polygons,all_triangles=False)
    error=max(max((old_tree.find_nearest(p)[3] for p in points),default=0.),
              max((tree.find_nearest(p)[3] for p in original),default=0.))
    if not math.isfinite(error) or error>.006:
        bpy.data.meshes.remove(reduced)
        raise ValueError('Cloth conditioning would change garment silhouette by more than 6 mm')
    old=obj.data;obj.data=reduced
    if old.users==0:bpy.data.meshes.remove(old)
    pin=obj.vertex_groups.get('FitMeSupport')
    if pin:obj.vertex_groups.remove(pin)
    return {'applied':True,'method':'native_decimate','input_vertices':before,
            'vertices':len(points),'triangles':len(polygons),'sampled_surface_error_m':float(error),
            'display_body_modified':False}


def _relax_folds(obj,body_vertices,body_faces,*,trigger_m=.016,offset_m=.020):
    """Smooth only newly folded patches; keep the original mesh connectivity."""
    faces=triangulate([tuple(p.vertices) for p in obj.data.polygons])
    neighbors=[set() for _ in obj.data.vertices]
    for edge in obj.data.edges:
        a,b=edge.vertices;neighbors[a].add(b);neighbors[b].add(a)
    history=[]
    for iteration in range(9):
        points=[v.co.copy() for v in obj.data.vertices]
        tree=BVHTree.FromPolygons(points,faces,all_triangles=True)
        touched=set();count=0
        for a,b in tree.overlap(tree):
            if a>=b or set(faces[a]).intersection(faces[b]):continue
            if triangle_intersection([points[i] for i in faces[a]],[points[i] for i in faces[b]]):
                touched.update(faces[a]);touched.update(faces[b]);count+=1
        history.append(count)
        if not count or iteration==8:break
        group=obj.vertex_groups.new(name='FitMeSizingFolds')
        modifier=None
        try:
            frontier=touched;seen=set()
            for weight in (1.,.8,.5,.2):
                group.add(sorted(frontier),weight,'REPLACE');seen.update(frontier)
                frontier={j for i in frontier for j in neighbors[i]}-seen
                if not frontier:break
            modifier=obj.modifiers.new('SAM local fold relaxation','SMOOTH')
            modifier.vertex_group=group.name;modifier.factor=.5;modifier.iterations=10
            bpy.context.view_layer.update()
            points=[v.co.copy() for v in obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
            obj.modifiers.remove(modifier);modifier=None
            _set_points(obj,points)
        finally:
            if modifier:obj.modifiers.remove(modifier)
            obj.vertex_groups.remove(group)
        _outside(obj,body_vertices,body_faces,trigger_m=trigger_m,offset_m=offset_m)
    return {'method':'native_local_smooth_and_outside','self_crossings_history':history,
            'iterations':len(history)-1,'complete':history[-1]==0}


def _resize_lower_body(obj,anchors,body,vertices,faces,landmarks,measurements):
    source=np.asarray([v.co[:] for v in obj.data.vertices]);bottom=float(body[:,2].min())
    waist=landmarks.get('fit_anchor_waist')
    if waist is None or not all(math.isfinite(v) for v in waist):raise ValueError('Missing SAM waist anchor')
    target_height=float(waist.z-bottom)-.02;old_height=float(np.ptp(source[:,2]))
    if min(target_height,old_height)<.2:raise ValueError('Invalid SAM lower-body sizing height')
    hip=_measurement_height(measurements,'hip_line_height_cm',bottom,bottom+np.ptp(body[:,2])*.49)
    row=torso_contour(body,np.asarray(triangulate(faces),dtype=int),hip)
    if len(row)<8:raise ValueError('Missing SAM hip sizing surface')
    width=float(np.ptp(row[:,0]))+.035;depth=float(np.ptp(row[:,1]))+.035
    current=np.ptp(source,axis=0)
    if np.any(current<1e-6):raise ValueError('Degenerate lower-body template')
    center=(source.min(0)+source.max(0))/2;top=float(source[:,2].max())
    target_center=(row[:,:2].min(0)+row[:,:2].max(0))/2
    scales=np.array([width/current[0],depth/current[1],target_height/old_height])
    source[:,:2]=(source[:,:2]-center[:2])*scales[:2]+target_center
    source[:,2]=waist.z+(source[:,2]-top)*scales[2]
    _set_points(obj,source);_outside(obj,vertices,faces)
    for anchor in anchors:
        if anchor['name']=='fit_anchor_waist':continue
        x,z,y=anchor['translation'];point=np.array([x,-y,z],dtype=float)
        point[:2]=(point[:2]-center[:2])*scales[:2]+target_center
        point[2]=waist.z+(point[2]-top)*scales[2]
        anchor['translation']=[float(point[0]),float(point[2]),float(-point[1])]
    repair=_relax_folds(obj,vertices,faces)
    conditioning=_condition_cloth_mesh(obj);_outside(obj,vertices,faces)
    final_repair=_relax_folds(obj,vertices,faces)
    return {'method':'sam_lower_body_and_native_shrinkwrap','size_source':'sam_surface',
            'catalog_measurements_used':False,'spring_reference':'sam_sized_template','clearance_m':.012,
            'fold_relaxation':repair,'cloth_conditioning':conditioning,'final_fold_relaxation':final_repair}
