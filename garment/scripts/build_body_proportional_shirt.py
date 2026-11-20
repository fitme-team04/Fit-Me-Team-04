# 역할: 실제 인체 어깨 표면을 기준으로 상의 4개 치수만 적용하고 나머지는 고정 비율로 생성합니다.
import argparse,json,sys
from pathlib import Path
import bpy,bmesh
import numpy as np
from mathutils import Vector
from scipy import sparse
from scipy.spatial import ConvexHull
from scipy.sparse.linalg import spsolve

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from core.garment_specs import validate_spec
from geometry.template_binding import geometry
from geometry.body_clearance import require_clear
from prepare_template import register
from rebuild_smooth_shirt import connected_components
from rebuild_cc0_reference import vertices_world,triangles,inspect,boundary_loops,save_anchor_bindings,tree,signed_points

RATIOS={'hem_below_hip_to_shoulder':0.,'shoulder_ease':1.05,'chest_ease':1.10,
        'sleeve_to_body_arm':1.,'hem_to_shoulder':.94,'neck_to_shoulder':.42,
        'neck_depth_to_width':1.05,'neck_rise_to_shoulder':.15,'fabric_gap_to_chest':.012,
        'depth_ease_ratio':1.10,'arm_blend_width_to_body_shoulder':.20,'arm_blend_length_to_body_arm':.15}

STYLE_V15={'waist_inset':.055,'waist_blend_to_length':.16,'fairing_strength':.45,'fairing_passes':32,
           'minimum_gap_to_chest':.008,'sleeve_cuff_radius_to_chest':.075,'sleeve_join_to_length':.30,
           'sleeve_transition_fraction':.18}


def refine_style(vertices,faces,body,body_faces,ref,spec,anchors,body_center):
    """Fixed template ratios; no extra editable garment measurement."""
    result=vertices.copy();length=spec['body_length']/100;shoulder=spec['garment_shoulder_width']/100
    chest=spec['chest_width']/100;run=spec['sleeve_length']/100
    waist_z=ref['waist_line_height_cm']/100
    waist_t=np.abs(result[:,2]-waist_z)/(length*STYLE_V15['waist_blend_to_length'])
    waist_weight=np.where(waist_t<1,np.cos(np.minimum(waist_t,1)*np.pi/2)**2,0)
    waist_weight*=smooth((shoulder*.65-np.abs(result[:,0]))/(shoulder*.15))
    scale=1-STYLE_V15['waist_inset']*waist_weight
    result[:,0]*=scale
    centers=np.array([body_center(z) for z in result[:,2]])
    result[:,1]=centers+(result[:,1]-centers)*scale
    edges=np.unique(np.sort(np.vstack((faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]])),axis=1),axis=0)
    a,b=edges.T;links=sparse.coo_matrix((np.ones(2*len(a)),(np.r_[a,b],np.r_[b,a])),shape=(len(result),len(result))).tocsr()
    degree=np.maximum(1,np.asarray(links.sum(1)).ravel())
    chest_z=ref['chest_line_height_cm']/100
    weight=smooth((np.abs(result[:,0])-shoulder*.20)/(shoulder*.12))*smooth((result[:,2]-chest_z)/(length*.15))
    for label in ('L','R'):
        origin=np.array(anchors['fit_shoulder_'+label].translation);axis=np.array(anchors['fit_wrist_'+label].translation)-origin;axis/=np.linalg.norm(axis)
        t=(result-origin)@axis;side=1 if label=='L' else -1
        arm=smooth((side*result[:,0]-shoulder*.43)/(shoulder*.16))*smooth((run-t)/(run*.20))
        weight=np.maximum(weight,arm)
    border=np.concatenate(boundary_loops(faces));weight[border]=0
    obstacle=tree(body,body_faces);minimum=chest*STYLE_V15['minimum_gap_to_chest']
    original=result.copy()
    rejected=0
    for _ in range(STYLE_V15['fairing_passes']):
        previous=result.copy()
        delta=(links@result/degree[:,None]-result)*weight[:,None]*STYLE_V15['fairing_strength']
        # Reject/damp inward candidates rather than pushing any point through the body.
        for index in np.flatnonzero(np.linalg.norm(delta,axis=1)>1e-8):
            movement=delta[index]
            for attempt in range(7):
                candidate=result[index]+movement
                nearest,normal,_,_=obstacle.find_nearest(Vector(candidate))
                if (Vector(candidate)-nearest).dot(normal)>=minimum:
                    result[index]=candidate;break
                movement*=.5
        for rollback in range(5):
            pairs=tree(result,faces).overlap(obstacle)
            if not pairs:break
            ids=np.unique(faces[np.unique(np.asarray(pairs)[:,0])])
            result[ids]=previous[ids];rejected+=len(ids)
        else:result=previous
    # Straight shoulder roof: outward-only linear slope with a distinct outer seam.
    for side in (-1,1):
        ax=side*result[:,0];start=shoulder*.25;stop=shoulder*.57
        band=(ax>start)&(ax<stop)&(result[:,2]>anchors['fit_anchor'].translation.z-.015)
        target=anchors['fit_anchor'].translation.z+.025-(ax-start)*.38
        lift=np.clip(target-result[:,2],0,.012)
        result[band,2]+=lift[band]
    fairing_result=result.copy()
    return result,{'fixed_style_ratios':STYLE_V15,'maximum_fairing_shift_mm':float(np.linalg.norm(fairing_result-original,axis=1).max()*1000),
                   'waist_inset_ratio':STYLE_V15['waist_inset'],'body_obstacle_projection_used':False,'rolled_back_vertex_updates':rejected}


def smooth(t):
    t=np.clip(t,0,1);return t*t*(3-2*t)


def ordered_loop(bm,ids):
    ids=set(ids);adj={}
    for edge in bm.edges:
        if edge.is_boundary and all(v.index in ids for v in edge.verts):
            a,b=edge.verts;adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
    if any(len(v)!=2 for v in adj.values()):raise ValueError('Invalid torso join loop')
    current=next(iter(adj));result=[current];previous=None
    while True:
        nxt=next(v for v in adj[current] if v!=previous)
        if nxt==result[0]:break
        result.append(nxt);previous,current=current,nxt
    if len(result)!=len(ids):raise ValueError('Torso join is fragmented')
    return result


def rebuild_clean_sleeves(obj,body,ref,spec,anchors):
    """Join a continuous tapered surface to each proximal sleeve, without separate caps."""
    run=spec['sleeve_length']/100;chest=spec['chest_width']/100;S=spec['garment_shoulder_width']/100
    bodyS=ref['shoulder_width_cm']/100;details={}
    bm=bmesh.new();bm.from_mesh(obj.data)
    for side,label in ((-1,'R'),(1,'L')):
        origin=np.array(anchors['fit_shoulder_'+label].translation);axis=np.array(anchors['fit_wrist_'+label].translation)-origin;axis/=np.linalg.norm(axis)
        origin+=axis*((S-bodyS)/2/abs(axis[0]));cut=run*STYLE_V15['sleeve_join_to_length'];plane=origin+axis*cut
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
            plane_co=plane,plane_no=axis,dist=1e-7)
        remove=[f for f in bm.faces if side*f.calc_center_median().x>bodyS*.58 and (np.array(f.calc_center_median())-plane)@axis>1e-7]
        bmesh.ops.delete(bm,geom=remove,context='FACES')
        loose=[v for v in bm.verts if not v.link_faces]
        if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
        bm.verts.index_update()
        border=[e for e in bm.edges if e.is_boundary and all(side*v.co.x>bodyS*.58 and abs((np.array(v.co)-plane)@axis)<1e-5 for v in e.verts)]
        previous=ordered_loop(bm,{v.index for e in border for v in e.verts})
        join=np.array([v.co[:] for v in previous]);join_center=join.mean(0);end=origin+axis*run
        loft_axis=end-join_center;loft_length=np.linalg.norm(loft_axis);loft_axis/=loft_length
        radial=join-join_center;radial-=np.outer(radial@loft_axis,loft_axis)
        direction=radial/np.maximum(np.linalg.norm(radial,axis=1),1e-8)[:,None]
        cuff=chest*STYLE_V15['sleeve_cuff_radius_to_chest'];upper=np.linalg.norm(radial,axis=1)
        relative=body-join_center;t=relative@loft_axis;r=np.linalg.norm(relative-t[:,None]*loft_axis,axis=1)
        mask=(side*body[:,0]>bodyS*.58)&(t>=0)&(t<loft_length-.001)&(r<chest*.18)
        p=np.clip(t[mask]/loft_length,0,.999)
        near_wrist=p>.85
        if near_wrist.any():cuff=max(cuff,float(np.max(r[mask][near_wrist]+chest*.008)))
        upper=np.maximum(upper,cuff)
        proximal=p<=.85
        for point,rr,progress in zip(relative[mask][proximal],r[mask][proximal],p[proximal]):
            ray=point-loft_axis*(point@loft_axis);ray/=max(np.linalg.norm(ray),1e-9)
            index=int(np.argmax(direction@ray));required=(rr+chest*.008-progress*cuff)/(1-progress)
            for neighbor in ((index-1)%len(upper),index,(index+1)%len(upper)):
                upper[neighbor]=max(upper[neighbor],required)
        # Convex radial envelope removes inward grooves without flattening the sleeve.
        basis_a=direction[0];basis_b=np.cross(loft_axis,basis_a);basis_b/=np.linalg.norm(basis_b)
        uv=np.column_stack((direction@basis_a,direction@basis_b))
        hull=ConvexHull(uv*upper[:,None])
        equations=hull.equations
        for index,ray in enumerate(uv):
            denom=equations[:,:2]@ray
            valid=denom>1e-9
            upper[index]=min(-equations[valid,2]/denom[valid])
        for amount in np.linspace(0,1,33)[1:]:
            center=join_center+(end-join_center)*amount;radius=upper*(1-amount)+cuff*amount
            desired=center+direction*radius[:,None]
            base=join+(end-join_center)*amount
            blend=smooth(amount/STYLE_V15['sleeve_transition_fraction']);points=base*(1-blend)+desired*blend
            current=[bm.verts.new(point) for point in points]
            for i in range(len(previous)):
                j=(i+1)%len(previous);bm.faces.new((previous[i],previous[j],current[j],current[i]))
            previous=current
        details[label]={'join_vertices':len(join),'upper_radius_cm':[float(upper.min()*100),float(upper.max()*100)],'cuff_radius_cm':cuff*100}
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    return (*geometry(obj),details)


def main():
    p=argparse.ArgumentParser()
    for name in ('body','reference-measurements','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--spec-json',type=Path)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'models/registry.json').exists():raise ValueError('Use a fresh output directory for each four-input regeneration')
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(args.body.resolve()))
    body_obj=next(o for o in bpy.context.scene.objects if o.type=='MESH');body_obj.name='ReferenceBody'
    body=vertices_world(body_obj);body_faces=triangles(body_obj)
    anchors={o.name:o.matrix_world.copy() for o in bpy.context.scene.objects if o.name.startswith('fit_')}
    metadata=json.loads(args.reference_measurements.read_text(encoding='utf-8'))['measurements']
    ref={k:float(v['measured']) for k,v in metadata.items()}
    height=float(np.ptp(body[:,2])*100)
    if abs(height-ref['height_cm'])>.5:raise ValueError('Reference measurements belong to a different body')
    body_shoulder=float(abs(anchors['fit_shoulder_L'].translation.x-anchors['fit_shoulder_R'].translation.x)*100)
    body_arm=float(np.mean([(anchors['fit_wrist_'+side].translation-anchors['fit_shoulder_'+side].translation).length*100 for side in ('L','R')]))
    default={'body_length':0.,
        'garment_shoulder_width':round(body_shoulder*RATIOS['shoulder_ease'],2),
        'chest_width':round(ref['chest_girth_cm']/2*RATIOS['chest_ease'],2),
        'sleeve_length':round(body_arm*RATIOS['sleeve_to_body_arm'],2)}
    high_point=float(anchors['fit_anchor'].translation.z)*100+default['garment_shoulder_width']*RATIOS['neck_rise_to_shoulder']
    default['body_length']=round(high_point-ref['hip_line_height_cm']+default['garment_shoulder_width']*RATIOS['hem_below_hip_to_shoulder'],2)
    shoulder_drop=(default['garment_shoulder_width']-body_shoulder)/2
    axis=anchors['fit_wrist_L'].translation-anchors['fit_shoulder_L'].translation;axis.normalize()
    default['sleeve_length']=float(round(body_arm-shoulder_drop/abs(axis.x),2))
    supplied=json.loads(args.spec_json.read_text()) if args.spec_json else default
    if set(supplied)!=set(default):raise ValueError('Exactly four garment measurements are configurable')
    spec=validate_spec('crewneck',supplied,'shoulder')
    L,S,C,U=[spec[k]/100 for k in ('body_length','garment_shoulder_width','chest_width','sleeve_length')]
    anchor_z=float(anchors['fit_anchor'].translation.z)
    neck_z=anchor_z+S*RATIOS['neck_rise_to_shoulder'];hem_z=neck_z-L
    join_z=ref['waist_line_height_cm']/100-S*.20
    if not hem_z<join_z-.02:raise ValueError('Shirt length too short for the reference proportions')
    shirt=body_obj.copy();shirt.data=body_obj.data.copy();shirt.name='ProportionalShirt';bpy.context.collection.objects.link(shirt)
    shirt.data.transform(shirt.matrix_world);shirt.matrix_world.identity()
    bm=bmesh.new();bm.from_mesh(shirt.data)
    planes=[((0,0,join_z),(0,0,-1)),((0,0,neck_z),(0,0,1))]
    for label in ('L','R'):
        shoulder=np.array(anchors['fit_shoulder_'+label].translation);wrist=np.array(anchors['fit_wrist_'+label].translation)
        axis=wrist-shoulder;axis/=np.linalg.norm(axis);planes.append((wrist,axis))
    for point,normal in planes:
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=point,plane_no=normal,dist=1e-7,clear_outer=True)
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(shirt.data);bm.free();shirt.data.update()
    original,faces=geometry(shirt)
    loops=boundary_loops(faces)
    if len(loops)!=4:raise ValueError('Body extraction did not produce four openings')
    chest_z=ref['chest_line_height_cm']/100
    chest_scale=2*C/(ref['chest_girth_cm']/100)
    sleeve_scale=U/(body_arm/100);gap=C*RATIOS['fabric_gap_to_chest']
    # Preserve the anatomical shoulder surface; place the garment seam along the actual arm axis.
    top_weight=smooth((original[:,2]-chest_z)/(anchor_z-chest_z))
    torso=original.copy();torso[:,0]*=chest_scale+(1.-chest_scale)*top_weight
    torso[:,1]*=chest_scale
    result=torso.copy()
    for side,label in ((-1,'R'),(1,'L')):
        shoulder=np.array(anchors['fit_shoulder_'+label].translation);wrist=np.array(anchors['fit_wrist_'+label].translation)
        axis=wrist-shoulder;axis/=np.linalg.norm(axis)
        shift=(S-body_shoulder/100)/2
        target_shoulder=shoulder+axis*(shift/abs(axis[0]))
        relative=original-shoulder;t=relative@axis;radial=relative-t[:,None]*axis
        moved=target_shoulder+t[:,None]*sleeve_scale*axis+radial*chest_scale
        blend_width=body_shoulder/100*RATIOS['arm_blend_width_to_body_shoulder']
        blend_length=body_arm/100*RATIOS['arm_blend_length_to_body_arm']
        weight=smooth((side*original[:,0]-body_shoulder/200+body_shoulder/100*.04)/blend_width)*smooth(t/blend_length)
        result=result*(1-weight[:,None])+moved*weight[:,None]
    # An open cropped surface may be reoriented inward by Blender. Use the closed body's normals.
    reference_tree=tree(body,body_faces)
    normals=np.array([reference_tree.find_nearest(Vector(point))[1] for point in original])
    result+=normals*gap
    # Straight lower-torso taper; section depth retains the body's chest depth/width ratio.
    depth_ratio=ref['chest_depth_cm']/ref['chest_width_cm']*RATIOS['depth_ease_ratio']
    chest_rx=ref['chest_width_cm']/200*chest_scale+gap
    hem_rx=S*RATIOS['hem_to_shoulder']/2
    chest_points=body[(np.abs(body[:,2]-chest_z)<.008)&(np.abs(body[:,0])<.23)]
    center_y=float((chest_points[:,1].min()+chest_points[:,1].max())/2)
    levels=np.array([ref['hip_line_height_cm']/100,ref['waist_line_height_cm']/100,chest_z])
    centers=[]
    for level in levels:
        q=body[(np.abs(body[:,2]-level)<.012)&(np.abs(body[:,0])<.23)]
        centers.append(float((q[:,1].min()+q[:,1].max())/2))
    def body_center(z):return float(np.interp(z,levels,centers))
    for i,point in enumerate(result):
        x,y,z=point
        if original[i,2]<chest_z and abs(original[i,0])<body_shoulder/100*.55:
            t=np.clip((chest_z-z)/(chest_z-hem_z),0,1);rx=(1-t)*chest_rx+t*hem_rx;ry=rx*depth_ratio+gap
            cy=body_center(z);theta=np.arctan2(y-cy,x)
            target=np.array([rx*np.cos(theta),cy+ry*np.sin(theta)])
            w=.97*smooth((chest_z-z)/(.22*L))*smooth((S*.60-abs(x))/(S*.12))
            result[i,:2]=(1-w)*point[:2]+w*target
    # Neck size is proportional to shoulder width; smooth only the neck band, not the shoulder cap.
    neck=max(loops,key=lambda ids:original[ids,2].mean())
    center=(result[neck,:2].min(0)+result[neck,:2].max(0))/2;theta=np.arctan2(result[neck,1]-center[1],result[neck,0]-center[0])
    neck_rx=S*RATIOS['neck_to_shoulder']/2;neck_ry=neck_rx*RATIOS['neck_depth_to_width']
    target=np.column_stack((center[0]+neck_rx*np.cos(theta),center[1]+neck_ry*np.sin(theta),np.full(len(neck),neck_z)))
    edges=np.unique(np.sort(np.vstack((faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]])),axis=1),axis=0)
    a,b=edges.T;links=sparse.coo_matrix((np.ones(2*len(a)),(np.r_[a,b],np.r_[b,a])),shape=(len(result),len(result))).tocsr()
    lap=sparse.diags(np.asarray(links.sum(1)).ravel())-links
    fixed=(original[:,2]<anchor_z+S*.04)|(np.abs(original[:,0])>S*.30);fixed[neck]=True
    delta=np.zeros_like(result);delta[neck]=target-result[neck];free=np.flatnonzero(~fixed);bound=np.flatnonzero(fixed)
    delta[free]=spsolve((lap[free][:,free]+.02*sparse.eye(len(free))).tocsc(),-lap[free][:,bound]@delta[bound]);result+=delta
    shirt.data.vertices.foreach_set('co',result.ravel());shirt.data.update()
    # Extend the torso using the same proportional hem and depth, welding directly to its join.
    hem_join=min(loops,key=lambda ids:original[ids,2].mean())
    bm=bmesh.new();bm.from_mesh(shirt.data);bm.verts.ensure_lookup_table();bm.verts.index_update()
    previous=ordered_loop(bm,hem_join);join=np.array([v.co[:] for v in previous]);theta=np.arctan2(join[:,1]-body_center(float(join[:,2].mean())),join[:,0])
    for amount in np.linspace(0,1,25)[1:]:
        z=float(join[:,2].mean()+(hem_z-join[:,2].mean())*amount)
        t=np.clip((chest_z-z)/(chest_z-hem_z),0,1);rx=(1-t)*chest_rx+t*hem_rx;ry=rx*depth_ratio+gap
        desired=np.column_stack((rx*np.cos(theta),body_center(z)+ry*np.sin(theta),np.full(len(theta),z)))
        base=join.copy();base[:,2]=z;w=smooth(amount/.25);points=(1-w)*base+w*desired
        current=[bm.verts.new(p) for p in points]
        for i in range(len(previous)):
            j=(i+1)%len(previous);bm.faces.new((previous[i],previous[j],current[j],current[i]))
        previous=current
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(shirt.data);bm.free();shirt.data.update()
    v,f=geometry(shirt)
    face_normal=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
    reference_normal=np.array([reference_tree.find_nearest(Vector(p))[1] for p in v[f].mean(1)])
    if np.median(np.einsum('ij,ij->i',face_normal,reference_normal))<0:
        bm=bmesh.new();bm.from_mesh(shirt.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(shirt.data);bm.free();shirt.data.update();v,f=geometry(shirt)
    v,style_report=refine_style(v,f,body,body_faces,ref,spec,anchors,body_center)
    shirt.data.vertices.foreach_set('co',v.ravel());shirt.data.update()
    v,f,sleeve_report=rebuild_clean_sleeves(shirt,body,ref,spec,anchors)
    # Fill only the upper proximal sleeve silhouette; preserve the lower half.
    upper_fill=0.
    for side,label in ((-1,'R'),(1,'L')):
        origin=np.array(anchors['fit_shoulder_'+label].translation)
        wrist=np.array(anchors['fit_wrist_'+label].translation)
        ax=side*v[:,0];start=S*.48;stop=S*.96
        axis_z=origin[2]+(ax-side*origin[0])*(wrist[2]-origin[2])/(side*(wrist[0]-origin[0]))
        ids=np.flatnonzero((ax>=start)&(ax<=stop)&(v[:,2]>axis_z))
        hull=ConvexHull(np.column_stack((ax[ids],v[ids,2])))
        equations=hull.equations;top=equations[equations[:,1]>1e-8]
        roof=np.min((-top[:,2,None]-top[:,0,None]*ax[ids])/top[:,1,None],axis=0)
        section_top=np.maximum(roof-axis_z[ids],1e-6)
        upper_weight=smooth((v[ids,2]-axis_z[ids])/section_top)
        lift=np.maximum(0,roof-v[ids,2])*upper_weight
        # Apply the full correction at the top, fading to zero at the arm axis.
        v[ids,2]+=lift
        upper_fill=max(upper_fill,float(lift.max()*1000))
    shirt.data.vertices.foreach_set('co',v.ravel());shirt.data.update()
    style_report['upper_sleeve_fill_max_mm']=upper_fill
    # Taper only the bottom side edges; retain the front/back depth and upper waist.
    hem_weight=smooth((hem_z+L*.14-v[:,2])/(L*.14))
    side_weight=smooth((np.abs(v[:,0])-S*.20)/(S*.20))
    v[:,0]*=1-.025*hem_weight*side_weight
    shirt.data.vertices.foreach_set('co',v.ravel());shirt.data.update()
    style_report['hem_side_inset_ratio']=.025
    # Remove the lower-abdomen side bulge with a straight, gently tapered envelope.
    lower_top=ref['waist_line_height_cm']/100+.035
    progress=np.clip((lower_top-v[:,2])/(lower_top-hem_z),0,1)
    half_width=S*.94/2*(.97-.01*progress)
    affected=(v[:,2]<lower_top)&(np.abs(v[:,0])>half_width)&(np.abs(v[:,0])<S*.65)
    target=v.copy();target[affected,0]=np.sign(v[affected,0])*half_width[affected]
    # The final exact body test below rejects any unsafe correction.
    v=target
    shirt.data.vertices.foreach_set('co',v.ravel());shirt.data.update()
    style_report['lower_abdomen_straight_envelope']=True
    style_report['continuous_sleeves']=sleeve_report
    check=inspect(v,f,body,body_faces)
    report={'spec_cm':spec,'body_reference_cm':{'height':height,'shoulder':body_shoulder,'chest_girth':ref['chest_girth_cm'],'arm_length':body_arm},
        'fixed_ratios':RATIOS,'configurable_fields':list(default),'body_projection_used':False,'pants_hidden':True,'body_check':check,
        'hem_width_derived_cm':S*RATIOS['hem_to_shoulder']*100,'depth_ratio':depth_ratio,
        'components':len(connected_components(f,len(v))),'openings':len(boundary_loops(f)),'style_refinement':style_report}
    (out/'proportional-report.json').write_text(json.dumps(report,indent=2)+'\n')
    signed=signed_points(v,tree(body,body_faces));bad=v[signed<-.00001]
    if len(bad):print('BAD_REGIONS '+json.dumps({'min':bad.min(0).tolist(),'max':bad.max(0).tolist(),
        'upper':int((bad[:,2]>chest_z).sum()),'lower':int((bad[:,2]<=chest_z).sum()),
        'neck':int((bad[:,2]>anchor_z+.015).sum()),'arms':int((np.abs(bad[:,0])>.24).sum())}),flush=True)
    print('PROPORTIONAL_CHECK '+json.dumps(report),flush=True);require_clear(check)
    if report['components']!=1 or report['openings']!=4:raise ValueError('Shirt connectivity invalid')
    mat=bpy.data.materials.new('MatteBlackCotton');mat.use_nodes=True;mat.diffuse_color=(.018,.020,.023,1)
    node=mat.node_tree.nodes.get('Principled BSDF');node.inputs['Base Color'].default_value=mat.diffuse_color;node.inputs['Roughness'].default_value=.95
    shirt.data.materials.clear();shirt.data.materials.append(mat)
    uv=shirt.data.uv_layers.new(name='ProportionalGarmentUV')
    for poly in shirt.data.polygons:
        poly.use_smooth=True
        for i in poly.loop_indices:
            x,y,z=v[shirt.data.loops[i].vertex_index];uv.data[i].uv=((np.arctan2(y-center_y,x)+np.pi)/(2*np.pi),z/height*100)
    placement=anchors['fit_anchor'];inverse=placement.inverted();local=np.array([inverse@Vector(p) for p in v])
    shirt.data.vertices.foreach_set('co',local.ravel());shirt.data.update()
    hidden=[(o,list(o.users_collection)) for o in bpy.context.scene.objects if o!=shirt]
    for o,collections in hidden:
        o.name='HiddenReference_'+o.name
        for collection in collections:collection.objects.unlink(o)
    models=out/'models';register(shirt,'crewneck',spec,'shoulder','body_proportional_shirt_v18',models,30.)
    path=models/'registry.json';r=json.loads(path.read_text());e=r['templates']['body_proportional_shirt_v18']
    points={'fit_anchor':np.zeros(3)}
    for label in ('L','R'):
        shoulder=np.array(anchors['fit_shoulder_'+label].translation);wrist=np.array(anchors['fit_wrist_'+label].translation)
        direction=wrist-shoulder;direction/=np.linalg.norm(direction)
        garment_shoulder=shoulder+direction*((S-body_shoulder/100)/2/abs(direction[0]))
        garment_cuff=garment_shoulder+direction*U
        points['fit_shoulder_'+label]=np.array(inverse@Vector(garment_shoulder))
        points['fit_cuff_'+label]=np.array(inverse@Vector(garment_cuff))
    e.update(revision='18',anchor_bindings=save_anchor_bindings(e,points),configurable_fields=list(default),fixed_ratios=RATIOS,fixed_style_ratios=STYLE_V15,
        deformation_policy='regenerate_four_input_ratios')
    path.write_text(json.dumps(r,indent=2)+'\n')
    for o,collections in hidden:
        for collection in collections:collection.objects.link(o)
    shirt.matrix_world=placement;shirt.name='ProportionalShirt';body_obj.name='ReferenceBody'
    bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(out/'reference-fitting.blend'),compress=True)
    (out/'garment-spec.json').write_text(json.dumps(spec,indent=2)+'\n')
    print('PASS: body-based shoulders, four inputs only, proportional geometry',flush=True)


if __name__=='__main__':main()
