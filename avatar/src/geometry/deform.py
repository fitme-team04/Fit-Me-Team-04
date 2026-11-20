# 역할: 목표 신체 치수에 맞게 Blender 제어 메시를 변형합니다.
import numpy as np

def sections(p, triangles, origin, normal):
    distance=(p-origin) @ normal
    signs=distance[triangles]>0
    cuts=triangles[signs.any(axis=1) & ~signs.all(axis=1)]
    graph={}
    for tri in cuts:
        ends=[]
        for i,j in zip(tri,np.roll(tri,1)):
            if (distance[i]>0)!=(distance[j]>0):
                ends.append(tuple(sorted((i,j))))
        a,b=ends
        graph.setdefault(a,[]).append(b)
        graph.setdefault(b,[]).append(a)
    loops=[]
    while graph:
        start=next(iter(graph)); current=start; previous=None; loop=[]
        while current in graph:
            loop.append(current)
            neighbors=graph.pop(current)
            nxt=next((n for n in neighbors if n!=previous),None)
            previous,current=current,nxt
        if current==start and len(loop)>3:
            edges=np.array(loop)
            i,j=edges.T
            alpha=distance[i]/(distance[i]-distance[j])
            loops.append((edges,alpha))
    return loops

def points(mesh,loop):
    edges,alpha=loop
    return mesh[edges[:,0]]*(1-alpha[:,None])+mesh[edges[:,1]]*alpha[:,None]

def perimeter(p):
    return np.linalg.norm(p-np.roll(p,1,axis=0),axis=1).sum()

def horizontal(p,tri,z):
    return sections(p,tri,np.array([0,0,z]),np.array([0,0,1]))

"""Asset-specific surface landmarks and sagittal rise measurement."""
import numpy as np
from scipy.optimize import brentq


def sagittal_path(p,tri,waist):
    # Avoid a plane exactly on the mesh symmetry seam. Clip crossing edges to waist.
    paths=[]
    for loop in sections(p,tri,np.array([.00037,0,0]),np.array([1,0,0])):
        q=points(p,loop)
        mask=q[:,2]<waist
        for start in np.flatnonzero(mask & ~np.roll(mask,1)):
            idx=[(start-1)%len(q), start]
            while mask[(idx[-1]+1)%len(q)]:
                idx.append((idx[-1]+1)%len(q))
            idx.append((idx[-1]+1)%len(q))
            if min(q[idx,2])<.74 or min(q[idx,2])>.80:continue
            path=(loop[0][idx],loop[1][idx])
            blends=[(waist-q[idx[i],2])/(q[idx[j],2]-q[idx[i],2]) for i,j in [(0,1),(-1,-2)]]
            paths.append((path,blends))
    if len(paths)!=1:raise ValueError(f"Expected one waist-to-crotch arc, found {len(paths)}")
    return paths[0]

def arc_points(p,data):
    path,blends=data
    q=points(p,path)
    for i,j,t in [(0,1,blends[0]),(-1,-2,blends[1])]:
        q[i]+=t*(q[j]-q[i])
    return q

def length(q):
    return np.linalg.norm(np.diff(q,axis=0),axis=1).sum()

def adjust_rise(result,p,data,crotch,hip,target):
    # Local sagittal depth change around the perineum, fading before other rings.
    w=np.clip((hip-.012-p[:,2])/.035,0,1)*np.clip((p[:,2]-.69)/.04,0,1)
    w*=np.exp(-(p[:,0]/.052)**2)
    mid=arc_points(result,data)
    cy=mid[np.argmin(mid[:,2]),1]
    delta=w*(result[:,1]-cy)
    def error(k):
        trial=result.copy()
        trial[:,1]+=k*delta
        return length(arc_points(trial,data))*100-target
    if abs(error(0))<.0001:return target
    left, right = error(-.8), error(1.2)
    if left*right > 0:
        factor = -.8 if abs(left) <= abs(right) else 1.2
    else:
        factor = brentq(error,-.8,1.2)
    result[:,1]+=factor*delta
    return float(length(arc_points(result,data))*100)

import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Quaternion
from scipy import sparse
from scipy.sparse.linalg import factorized
from scipy.optimize import brentq

def smooth(t):
    t=np.clip(t,0,1)
    return t*t*(3-2*t)

def rotate_y(p,deg):
    angle=np.radians(deg)
    c,s=np.cos(angle),np.sin(angle)
    return np.array([p[0]*c+p[2]*s,p[1],-p[0]*s+p[2]*c])

def loop_at(mesh,tri,origin,normal,guess):
    candidates=sections(mesh,tri,origin,normal)
    return min(candidates,key=lambda l:np.linalg.norm(points(mesh,l).mean(axis=0)-guess))

def control_matrix(loop,n):
    edges,a=loop
    return sparse.coo_matrix((np.column_stack((1-a,a)).ravel(),
        (np.repeat(np.arange(len(a)),2),edges.ravel())),shape=(len(a),n)).tocsr()

def boundary_solve(mesh,edges,rows,goals,rest):
    # Smooth sparse displacement over mesh edges. Extra positional penalty limits spread.
    n=len(mesh)
    i,j=edges.T
    links=sparse.coo_matrix((np.ones(2*len(i)),(np.r_[i,j],np.r_[j,i])),shape=(n,n)).tocsr()
    lap=sparse.diags(np.asarray(links.sum(axis=1)).ravel())-links
    C=sparse.vstack(rows).tocsr()
    stiffness=lap.T@lap+.12*lap+.004*sparse.eye(n)
    fit=factorized((stiffness+1e5*(C.T@C)).tocsc())
    posed=mesh+fit(np.asarray(1e5*C.T@(np.vstack(goals)-C@mesh)))
    # Local/global surface regularization distributes arm rotation across the shoulder.
    # Use the asset as the undeformed edge reference and retain the fitted targets.
    original=rest
    previous=posed.copy()
    i,j=np.r_[i,j],np.r_[j,i]
    ref=original[i]-original[j]
    anchored=.02
    global_fit=factorized((lap+anchored*sparse.eye(n)+1e4*(C.T@C)).tocsc())
    fixed=anchored*mesh+1e4*C.T@np.vstack(goals)
    for iteration in range(22):
        edge=posed[i]-posed[j]
        cov=np.zeros((n,3,3))
        np.add.at(cov,i,edge[:,:,None]*ref[:,None,:])
        u,_,vt=np.linalg.svd(cov)
        flip=np.linalg.det(u@vt)<0
        u[flip,:,-1]*=-1
        rotation=u@vt
        expected=np.einsum('ijk,ik->ij',(rotation[i]+rotation[j])*.5,ref)
        rhs=fixed.copy()
        np.add.at(rhs,i,expected)
        posed=global_fit(rhs)
    z=rest[:,2]
    influence=smooth((z-1.02)/.07)*smooth((1.43-z)/.09)
    return previous+(posed-previous)*influence[:,None]


def solve(sex,config,body=None):
    from mathutils import Matrix
    defaults={}

    if body is None:
        body=bpy.context.scene.objects['GEO-body_'+sex+'_realistic']
    mesh=body.data
    mesh.calc_loop_triangles()
    p=np.array([v.co[:] for v in body.data.shape_keys.reference_key.data])
    tri=np.array([t.vertices[:] for t in mesh.loop_triangles])
    edges=np.array([e.vertices[:] for e in mesh.edges])
    n=len(p)
    male=sex=="male"
    chest=1.191 if male else 1.187
    waist=1.004
    hip=.837 if male else .82
    low,top=p[:,2].min(),p[:,2].max()
    # Crotch height is where the two leg loops first form one central loop.
    lo,hi=.74,.79
    for _ in range(13):
        mid=(lo+hi)/2
        central=any(np.min(q[:,0])<0<np.max(q[:,0]) for q in
                    (points(p,l) for l in horizontal(p,tri,mid)))
        if central: hi=mid
        else: lo=mid
    crotch=(lo+hi)/2
    shoulder=np.array([.186,0,1.36] if male else [.165,0,1.335])
    elbow=np.array([.295,0,1.085] if male else [.245,0,1.07])
    wrist=np.array([.367,-.055,.904] if male else [.335,-.025,.887])
    # Arm length and angle use a straight shoulder-to-wrist reference.
    arm_vec=wrist-shoulder
    arm_len=np.linalg.norm(arm_vec)
    arm_angle=np.degrees(np.arctan2(arm_vec[0],-arm_vec[2]))
    base={"height_cm":(top-low)*100,"inseam_cm":(crotch-low)*100,
          "torso_length_cm":(shoulder[2]-waist)*100,"shoulder_width_cm":200*shoulder[0],
          "arm_length_cm":arm_len*100,"arm_angle_deg":arm_angle,
          "pelvis_tilt_deg":0.,"shoulder_tilt_deg":0.,"reference_pose":"asset"}
    rings=[]
    for label,z in [('hip',hip),('belly',(hip+waist)/2),('waist',waist),('chest',chest),('underbust',1.133 if male else 1.128)]:
        loop=loop_at(p,tri,[0,0,z],np.array([0,0,1]),[0,0,z])
        rings.append((label,0,loop))
        if label in ('chest','waist','hip'):base[label+"_line_height_cm"]=(z-low)*100
    for side in [-1,1]:
        for label,z in [('ankle',.095),('calf',.31),('knee',.454),('thigh',.666)]:
            loop=loop_at(p,tri,[0,0,z],np.array([0,0,1]),[side*.13,.015,z])
            rings.append((label,side,loop))
        for label,origin,direction in [('upper_arm',(shoulder+elbow)/2,elbow-shoulder),('wrist',wrist,wrist-elbow)]:
            mirror=np.array([side,1,1])
            loop=loop_at(p,tri,origin*mirror,direction*mirror,origin*mirror)
            rings.append((label,side,loop))
    for label,side,loop in rings:
        q=points(p,loop)
        key=label+'_girth_cm'
        base[key]=base.get(key,0)+perimeter(q)*100/(2 if side else 1)
        if not side and label in ('chest','waist','hip'):
            base[label+'_width_cm'],base[label+'_depth_cm']=np.ptp(q[:,:2],axis=0)*100
    arc=sagittal_path(p,tri,waist)
    raw_loops={label:points(p,loop) for label,side,loop in rings if not side}
    waist_y=(raw_loops['waist'][:,1].max()+raw_loops['waist'][:,1].min())/2
    base['belly_front_cm']=(waist_y-raw_loops['belly'][:,1].min())*100
    base['hip_rear_cm']=(raw_loops['hip'][:,1].max()-waist_y)*100
    base['rise_arc_cm']=length(arc_points(p,arc))*100
    marker_ids={}
    for side in (-1,1):
        for tag,guess in [('neck',(.067,.013,shoulder[2]+.05)),
                          ('tip',(shoulder[0],.0,shoulder[2]+.015)),
                          ('back',(.164 if male else .139,.07,1.242 if male else 1.222))]:
            target=np.array(guess)*[side,1,1]
            if tag=='back':
                # Posterior axillary proxies on the back, above the chest control ring.
                target=np.array([side*(.15 if male else .125),.078,1.265 if male else 1.245])
                candidates=np.flatnonzero((p[:,1]>.045)&(abs(p[:,0])<(.17 if male else .15)))
                marker_ids[tag,side]=int(candidates[np.argmin(np.linalg.norm(p[candidates]-target,axis=1))])
            else:
                marker_ids[tag,side]=int(np.argmin(np.linalg.norm(p-target,axis=1)))
    def slope(arr):
        angles=[]
        for side in (-1,1):
            d=arr[marker_ids['neck',side]]-arr[marker_ids['tip',side]]
            angles.append(np.degrees(np.arctan2(d[2],abs(d[0]))))
        return np.mean(angles)
    base['shoulder_slope_deg']=slope(p)
    li,ri=[marker_ids['back',s] for s in (-1,1)]
    base['back_width_cm']=(p[ri,0]-p[li,0])*100
    defaults[sex]={k:round(float(v),5) if k!='reference_pose' else v for k,v in base.items()}
    inputs=config.get(sex,{})
    if set(inputs)-set(base): raise ValueError(f"Unknown inputs: {set(inputs)-set(base)}")
    vals=dict(base)
    vals.update({k:v for k,v in inputs.items() if v is not None})
    for k in ('inseam_cm','torso_length_cm','hip_line_height_cm','waist_line_height_cm','chest_line_height_cm'):
        if inputs.get(k) is None:vals[k]=base[k]*vals['height_cm']/base['height_cm']
    if not -10<=vals['shoulder_slope_deg']<=45:raise ValueError('Shoulder slope must be -10..45 degrees')
    pose=vals['reference_pose']
    if pose not in ('asset','A','T'):raise ValueError("reference_pose: asset, A or T")
    if inputs.get('arm_angle_deg') is None and pose!='asset': vals['arm_angle_deg']={'A':45,'T':90}[pose]
    for k,v in vals.items():
        if k!='reference_pose' and (not isinstance(v,(int,float)) or not np.isfinite(v) or (k.endswith('_cm') and v<=0)):
            raise ValueError(f"Invalid {k}: {v}")
    if not 0<=vals['arm_angle_deg']<=90 or max(abs(vals[k]) for k in ('pelvis_tilt_deg','shoulder_tilt_deg'))>15:
        raise ValueError("Arm angle must be 0..90 and tilts within ±15 degrees")
    old=np.array([low,crotch,hip,waist,chest,shoulder[2],top])
    new=low+np.array([0,vals['inseam_cm'],vals['hip_line_height_cm'],vals['waist_line_height_cm'],
        vals['chest_line_height_cm'],vals['waist_line_height_cm']+vals['torso_length_cm'],vals['height_cm']])/100
    if new[-1]-new[0] < .015*(len(new)-1):
        raise ValueError('Body height is too short for valid landmark separation')
    for index in range(1,len(new)-1):
        new[index]=np.clip(new[index],new[index-1]+.015,new[-1]-.015*(len(new)-1-index))
    for key,index in [('inseam_cm',1),('hip_line_height_cm',2),('waist_line_height_cm',3),('chest_line_height_cm',4)]:
        vals[key]=float((new[index]-low)*100)
    vals['torso_length_cm']=float((new[-2]-new[3])*100)
    def warp(z):return np.interp(z,old,new)
    z=p[:,2]
    template=p.copy()
    template[:,2]=warp(z)
    # Isolate each arm below its armpit by mesh connectivity, then blend at the shoulder.
    from scipy.sparse.csgraph import connected_components
    i,j=edges.T
    graph=sparse.csr_matrix((np.ones(len(i)),(i,j)),shape=(n,n))
    cut=1.211 if male else 1.195
    arm_weight=np.zeros(n)
    for side in [-1,1]:
        ids=np.flatnonzero((z<cut)&(side*p[:,0]>.065))
        _,comp=connected_components(graph[ids][:,ids],directed=False)
        seed=np.argmin(np.linalg.norm(p[ids]-wrist*np.array([side,1,1]),axis=1))
        arm_weight[ids[comp==comp[seed]]]=1
    shoulder_blend=smooth((abs(p[:,0])-.075)/(shoulder[0]-.075))*smooth((z-cut+.035)/.05)*smooth((shoulder[2]+.07-z)/.07)
    arm_weight=np.maximum(arm_weight,shoulder_blend)
    # Smooth the topology mask across the armpit, including for a raised T pose.
    adjacent=(graph+graph.T).tocsr()
    degree=np.maximum(1,np.asarray(adjacent.sum(axis=1)).ravel())
    for _ in range(10):
        arm_weight=.5*arm_weight+.5*(adjacent@arm_weight)/degree
    def arm_transform(q,side):
        s=shoulder*np.array([side,1,1])
        shift=np.array([side*vals['shoulder_width_cm']/200,0,new[-2]])
        tilt=vals['shoulder_tilt_deg']
        hinge=np.array([0,0,new[-2]])
        shift=hinge+rotate_y(shift-hinge,-tilt)
        return shift+rotate_y((q-s)*(vals['arm_length_cm']/100/arm_len),-side*(vals['arm_angle_deg']-arm_angle))
    # Relative vertical tilt at hip and shoulder, fading into neighbouring body regions.
    tilt=np.interp(z,[crotch-.12,hip,waist,chest,shoulder[2],shoulder[2]+.10],
                   [0,vals['pelvis_tilt_deg'],0,0,vals['shoulder_tilt_deg'],0])
    template[:,2]+=p[:,0]*np.tan(np.radians(tilt))
    for side in (-1,1):
        idx=np.flatnonzero((side*p[:,0]>0)&(arm_weight>0))
        moved=np.array([arm_transform(q,side) for q in p[idx]])
        w=arm_weight[idx,None]
        template[idx]=(1-w)*template[idx]+w*moved
    rows=[];goals=[];meta=[]
    for label,side,loop in rings:
        C=control_matrix(loop,n)
        q=points(p,loop)
        center=(q.min(0)+q.max(0))/2
        delta=q-center
        ratio=1.
        if not side and label in ('chest','waist','hip'):
            # With one supplied dimension solve the other; with both use their ratio.
            wkey,dkey=label+'_width_cm',label+'_depth_cm'
            has_w=inputs.get(wkey) is not None
            has_d=inputs.get(dkey) is not None
            if has_w or has_d:
                sx,sy=vals[wkey]/base[wkey],vals[dkey]/base[dkey]
                if inputs.get(label+'_girth_cm') is None:
                    trial=delta.copy()
                    trial[:,:2]*=[sx,sy]
                    vals[label+'_girth_cm']=perimeter(trial)*100
                if has_w and has_d:ratio=sx/sy
                else:
                    def error(factor):
                        trial=delta.copy()
                        trial[:,:2]*=[sx,factor] if has_w else [factor,sy]
                        return perimeter(trial)*100-vals[label+'_girth_cm']
                    axis = 0 if has_w else 1
                    dimkey = wkey if has_w else dkey
                    span = np.ptp(delta[:,axis])
                    travel = np.abs(np.diff(delta[:,axis],append=delta[0,axis])).sum()
                    girth = vals[label+'_girth_cm']
                    limit = girth*span/travel
                    if error(0) >= 0:
                        vals[dimkey] = float(limit*(1-1e-4))
                        if has_w:
                            sx=vals[dimkey]/base[dimkey]
                        else:
                            sy=vals[dimkey]/base[dimkey]
                    other = delta[:,1-axis]
                    other_travel = np.abs(np.diff(other,append=other[0])).sum()
                    upper = 1 + girth/(100*other_travel)
                    factor=brentq(error,0,upper)
                    ratio=sx/factor if has_w else factor/sy
        delta[:,0]*=ratio
        delta*=vals[label+'_girth_cm']/100/perimeter(delta)
        if label in ('upper_arm','wrist'):
            target=np.array([arm_transform(center,side)+rotate_y(d,-side*(vals['arm_angle_deg']-arm_angle)) for d in delta])
        else:
            target=center+delta
            target[:,2]=warp(center[2])+delta[:,2]
            if label=='hip':
                h=np.array([0,0,warp(center[2])])
                target=np.array([h+rotate_y(v-h,-vals['pelvis_tilt_deg']) for v in target])
        if label=='belly' and inputs.get('belly_front_cm') is not None:
            target[:,1]+=waist_y-vals['belly_front_cm']/100-target[:,1].min()
        if label=='hip' and inputs.get('hip_rear_cm') is not None:
            target[:,1]+=waist_y+vals['hip_rear_cm']/100-target[:,1].max()
        if label == "wrist":
            tip = arm_transform(shoulder * np.array([side, 1, 1]), side)
            direction = target.mean(axis=0) - tip
            endpoint = tip + direction / np.linalg.norm(direction) * vals["arm_length_cm"] / 100
            target += endpoint - target.mean(axis=0)
        rows.append(C); goals.append(target); meta.append((label,side,C))
    markers={i:template[i].copy() for i in marker_ids.values()}
    if inputs.get('back_width_cm') is not None:
        center_x=(markers[ri][0]+markers[li][0])/2
        for i,side in [(ri,1),(li,-1)]:
            markers[i][0]=center_x+side*vals['back_width_cm']/200
    for side in (-1, 1):
        markers[marker_ids['tip', side]] = arm_transform(shoulder * np.array([side, 1, 1]), side)
    if inputs.get('shoulder_slope_deg') is not None:
        for side in (-1,1):
            a,b=[markers[marker_ids[tag,side]] for tag in ('neck','tip')]
            horizontal_span=abs(a[0]-b[0])
            a[2]=b[2]+horizontal_span*np.tan(np.radians(vals['shoulder_slope_deg']-side*vals['shoulder_tilt_deg']))
    ids=list(markers)
    rows.append(sparse.coo_matrix((np.ones(len(ids)),(np.arange(len(ids)),ids)),shape=(len(ids),n)).tocsr())
    goals.append(np.array(list(markers.values())))
    # Smoothly carry section displacements to adjacent skin.
    result=boundary_solve(template,edges,rows,goals,p)
    if inputs.get('rise_arc_cm') is not None:
        vals['rise_arc_cm']=adjust_rise(result,p,arc,crotch,hip,vals['rise_arc_cm'])
    return result, tri, rings, marker_ids, arc, vals
