# 역할: 슬랙스 기준 형상과 치수별 변형을 계산합니다.
"""Slacks cage geometry and measures (cm in, Blender metres out).

The runtime loads slacks_v1.blend and applies this cage through its .npz binding.
This module is the explicit entry point for waist/hip/rise/inseam/leg sizing.
"""
import math
import numpy as np
from geometry.glb import to_gltf

def slacks(spec):
    # A pair-of-pants surface: one waist boundary, two hem boundaries.
    # Front/back pelvic panels meet at the crotch saddle; no overlapping cylinders.
    half = 16
    u = np.linspace(-math.pi/2, math.pi/2, half+1)
    def ellipse(width, ratio):
        a=np.column_stack((np.sin(u), ratio*np.cos(u)))
        return a*(width/np.linalg.norm(np.diff(a,axis=0),axis=1).sum())
    pelvis_u=np.linspace(-math.pi/2, math.pi/2, 2*half+1)
    def pelvis(width):
        a=np.column_stack((np.sin(pelvis_u), .55*np.cos(pelvis_u)))
        return a*(width/np.linalg.norm(np.diff(a,axis=0),axis=1).sum())
    waist,hip=pelvis(spec['waist_width']),pelvis(spec['hip_width'])
    thigh,knee,hem=[ellipse(spec[k],.78) for k in ['thigh_width','knee_width','hem_width']]
    center=thigh[-1,0]
    # front_rise is the curved FRONT seam, not its vertical projection.
    front_y=np.array([waist[half,1],(.85*waist+.15*hip)[half,1],hip[half,1],hip[half,1]*.5,0])
    def front_arc(r):
        z=np.array([0,-3,-.55*r,-.80*r,-r])
        return float(np.hypot(np.diff(front_y),np.diff(z)).sum())
    low,high=6.,spec['front_rise']
    if front_arc(low)>spec['front_rise']:
        raise ValueError('front_rise too short for the waist/hip depth of this template')
    for _ in range(60):
        r=(low+high)/2
        if front_arc(r)<spec['front_rise']:low=r
        else:high=r
    rise=(low+high)/2
    # Preserve the requested inside-seam polyline length despite taper.
    dx1=thigh[-1,0]-knee[-1,0];dx2=knee[-1,0]-hem[-1,0]
    lo,hi=0.,spec['inseam']
    for _ in range(60):
        z=(lo+hi)/2
        arc=math.hypot(dx1,.55*z)+math.hypot(dx2,.45*z)
        if arc<spec['inseam']:lo=z
        else:hi=z
    drop=(lo+hi)/2
    verts=[];faces=[];lookup={};loops={}
    def vertex(p):
        p=np.asarray(p,dtype=float)
        key=tuple(np.round(p,9))
        if key not in lookup:lookup[key]=len(verts);verts.append(p)
        return lookup[key]
    def connect(previous,current,back):
        for i in range(len(previous)-1):
            a,b,c,d=previous[i],current[i],current[i+1],previous[i+1]
            if back:a,b,c,d=d,c,b,a
            for tri in [(a,b,c),(a,c,d)]:
                if len(set(tri))==3:faces.append(tri)
    for side in (-1,1):
        crotch=np.vstack((thigh+[-center,0], (thigh+[center,0])[1:]))
        upper=[]
        sections=[(waist,0),(.85*waist+.15*hip,-3),
                  (hip,-rise*.55),(.5*hip+.5*crotch,-rise*.80),(crotch,-rise)]
        for profile,z in sections:
            row=[vertex([x,side*y,z]) for x,y in profile]
            if upper:connect(upper[-1],row,side==1)
            upper.append(row)
        loops['waist',side]=upper[0];loops['hip',side]=upper[2]
        for direction,span in [(-1,slice(0,half+1)),(1,slice(half,2*half+1))]:
            previous=upper[-1][span]
            loops['thigh',direction,side]=previous
            for t,profile in [(0.275,.5*(thigh+knee)),(.55,knee),(.775,.5*(knee+hem)),(1.,hem)]:
                row=[vertex([direction*center+x,side*y,-rise-t*drop]) for x,y in profile]
                connect(previous,row,side==1)
                previous=row
                if t==.55:loops['knee',direction,side]=row
                if t==1:loops['hem',direction,side]=row
    vertices=np.array(verts)
    def length(ids):return float(np.linalg.norm(np.diff(vertices[ids],axis=0),axis=1).sum())
    metrics={'waist_width':length(loops['waist',-1]), 'hip_width':length(loops['hip',-1]),
             'front_rise':front_arc(rise),
             'inseam':float(math.hypot(dx1,.55*drop)+math.hypot(dx2,.45*drop)),
             **{k+'_width':length(loops[k,1,-1]) for k in ('thigh','knee','hem')}}
    anchors=[{'name':'fit_anchor_waist','translation':[0,0,0]},
             {'name':'fit_crotch','translation':[0,-rise/100,0]}]
    for side,label in [(-1,'R'),(1,'L')]:
        p=np.array([[side*center,0,-rise-drop]])/100
        anchors.append({'name':'fit_hem_'+label,'translation':to_gltf(p)[0].tolist()})
    return vertices/100,np.array(faces,dtype=int),anchors,metrics
