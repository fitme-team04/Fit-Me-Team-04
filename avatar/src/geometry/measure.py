# 역할: 생성된 신체 메시의 치수와 자세를 측정합니다.
"""Surface landmarks and actual exported geometry in Blender coordinates."""
import numpy as np
from mathutils import Matrix
from geometry.deform import points, perimeter, arc_points, length
from geometry.glb import to_gltf

def angle(d):
    return np.degrees(np.arctan2(d[2],abs(d[0])))

def analyze(p,rings,ids,arc,floor_override=None):
    sections={(tag,side):points(p,loop) for tag,side,loop in rings}
    v={'height_cm':np.ptp(p[:,2])*100}
    floor=p[:,2].min() if floor_override is None else floor_override
    for (tag,side),q in sections.items():
        k=tag+'_girth_cm'
        v[k]=v.get(k,0)+perimeter(q)*100/(2 if side else 1)
        if tag in ('hip','waist','chest'):
            v[tag+'_width_cm'],v[tag+'_depth_cm']=100*np.ptp(q[:,:2],axis=0)
            v[tag+'_line_height_cm']=(q[:,2].mean()-floor)*100
    def center(tag):
        q=sections[tag,0]
        return (q.max(0)+q.min(0))/2
    waist=center('waist')
    q=arc_points(p,arc)
    v.update(rise_arc_cm=100*length(q),inseam_cm=(q[:,2].min()-floor)*100,
             belly_front_cm=(waist[1]-sections['belly',0][:,1].min())*100,
             hip_rear_cm=(sections['hip',0][:,1].max()-waist[1])*100)
    tips=[p[ids['tip',s]] for s in (-1,1)]
    shoulder=np.mean(tips,axis=0)
    across=tips[1]-tips[0]
    v.update(shoulder_width_cm=100*across[0],shoulder_tilt_deg=angle(across),
             torso_length_cm=100*(shoulder[2]-waist[2]),
             back_width_cm=100*(p[ids['back',1],0]-p[ids['back',-1],0]))
    lengths=[];angles=[];slopes=[]
    for tip,side in zip(tips,(-1,1)):
        d=sections['wrist',side].mean(0)-tip
        lengths.append(np.linalg.norm(d)*100)
        angles.append(np.degrees(np.arctan2(abs(d[0]),-d[2])))
        slopes.append(angle(p[ids['neck',side]]-tip))
    v.update(arm_length_cm=np.mean(lengths),arm_angle_deg=np.mean(angles),shoulder_slope_deg=np.mean(slopes))
    hip=sections['hip',0]
    hip_axis=hip[hip[:,0].argmax()]-hip[hip[:,0].argmin()]
    v['pelvis_tilt_deg']=angle(hip_axis)
    frames=[]
    for name,origin,x in [('fit_anchor',shoulder,across),('fit_anchor_waist',waist,hip_axis)]:
        x=to_gltf(x[None,:])[0]
        x/=np.linalg.norm(x)
        z=np.cross(x,[0,1,0]);z/=np.linalg.norm(z)
        y=np.cross(z,x)
        quat=Matrix(np.column_stack((x,y,z)).tolist()).to_quaternion()
        frames.append({'name':name,'translation':to_gltf(origin[None,:])[0].tolist(),
                       'rotation':[quat.x,quat.y,quat.z,quat.w]})
    return v,frames
