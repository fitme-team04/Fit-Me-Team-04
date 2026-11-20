# 역할: 상의·하의 변형의 기준이 되는 케이지 형상을 만듭니다.
"""Deterministic deformation cages, cm input -> Blender metres (+Z up, -Y front)."""
import math
import numpy as np
from geometry.glb import to_gltf
from core.contract import FIXED_POSE
from geometry.slacks import slacks

CAGE_VERSION = 1


def back_neck_path(shoulder):
    points=[]
    for f in np.linspace(0,1,13):
        neck=max(0,1-(f/.5)**2)
        points.append([shoulder*f/2,neck*3,3*(1-f)-neck*2])
    return float(np.linalg.norm(np.diff(points,axis=0),axis=1).sum())

def crewneck(spec, sleeve_basis):
    length, shoulder, chest, sleeve = [spec[k] for k in
        ("body_length","garment_shoulder_width","chest_width","sleeve_length")]
    # The two panels wrap around the torso. Their chest cross-section
    # polylines each have the laid-flat length specified in the database.
    segments = 24
    u = np.linspace(-1,1,segments+1)
    outline = np.column_stack((np.sin(u*math.pi/2), .52*np.cos(u*math.pi/2)))
    outline *= chest/np.linalg.norm(np.diff(outline,axis=0),axis=1).sum()
    verts, faces, panels = [], [], []
    def vertex(point):
        verts.append(np.asarray(point))
        return len(verts)-1
    def quad(a,b,c,d,reverse=False):
        if reverse:
            a,b,c,d = d,c,b,a
        faces.extend([(a,b,c),(a,c,d)])
    arm_depth = .30*length
    for side in (-1,1):
        grid=[]
        for row,t in enumerate([0,.35,.70,1,1.65,2.45,3]):
            line=[]
            for col,f in enumerate(u):
                neck = max(0,1-(f/.5)**2)
                top = np.array([shoulder*f/2,side*neck*(5 if side<0 else 3),
                                3*(1-abs(f))-neck*(7 if side<0 else 2)])
                ring=np.array([outline[col,0],side*outline[col,1],1.5-arm_depth])
                if t<=1:
                    point=(1-t)*top+t*ring
                    point[1]+=side*3*abs(f)*math.sin(t*math.pi)
                else:
                    point=ring.copy()
                    point[2]-=(t-1)*(length-arm_depth)/2
                shared=(row==0 and abs(f)>=.5) or (row>=3 and col in (0,segments))
                if side==1 and shared:
                    line.append(panels[0][row][col])
                else:
                    line.append(vertex(point))
            grid.append(line)
            if row:
                for col in range(segments):
                    quad(grid[row-1][col],line[col],line[col+1],grid[row-1][col+1],side==1)
        panels.append(grid)
    anchors=[{"name":"fit_anchor","translation":[0,0,0]}]
    for direction,col in [(-1,0),(1,segments)]:
        opening=[panels[0][row][col] for row in range(4)]
        opening.extend(panels[1][row][col] for row in (2,1))
        if direction < 0:
            opening=[opening[0],*reversed(opening[1:])]
        shoulder_point=verts[opening[0]]
        back_top=np.array([verts[i] for i in panels[1][0]])
        neck_to_seam=np.linalg.norm(np.diff(back_top[segments//2:],axis=0),axis=1).sum()
        sleeve_run=sleeve-neck_to_seam if sleeve_basis=='center_back' else sleeve
        if sleeve_run<=0:
            raise ValueError("Sleeve specification shorter than neck-to-shoulder path")
        angle=math.radians(FIXED_POSE["arm_angle_deg"])
        # Forward reach of the A-pose wrist relative to projected arm length.
        axis=np.array([direction*math.sin(angle),-.11,-math.cos(angle)])
        axis/=np.linalg.norm(axis)
        inward=np.array([-direction*math.cos(angle),0,-math.sin(angle)])
        cross=np.cross(axis,inward)
        radius=chest*.10
        if sleeve_run<=radius:
            raise ValueError("Sleeve length is smaller than cuff radius")
        center=shoulder_point+axis*sleeve_run
        label="L" if direction>0 else "R"
        for tag,p in [("shoulder",shoulder_point),("cuff",center)]:
            anchors.append({"name":f"fit_{tag}_{label}","translation":to_gltf(p[None,:]/100)[0].tolist()})
        cuff=[]
        for index in range(len(opening)):
            angle=index*2*math.pi/len(opening)
            point=center-inward*math.cos(angle)*radius-cross*math.sin(angle)*chest*.09
            cuff.append(vertex(point))
        for i in range(len(opening)):
            j=(i+1)%len(opening)
            quad(opening[i],cuff[i],cuff[j],opening[j])
    metrics = {
        'body_length': float(max(v[2] for v in verts)-min(verts[i][2] for i in panels[0][-1])),
        'garment_shoulder_width': float(np.linalg.norm(verts[panels[0][0][-1]]-verts[panels[0][0][0]])),
        'chest_width': float(np.linalg.norm(np.diff(np.array([verts[i] for i in panels[0][3]]),axis=0),axis=1).sum()),
        'sleeve_length': float(np.linalg.norm(center-shoulder_point)+(neck_to_seam if sleeve_basis=='center_back' else 0)),
    }
    return np.array(verts)/100,np.array(faces),anchors,metrics


def cage(kind,spec,sleeve_basis):
    from core.garment_specs import validate_spec, complete_slacks_spec
    reference_spec = spec
    spec=validate_spec(kind,spec,sleeve_basis)
    if kind == 'slacks':
        spec = complete_slacks_spec(spec, reference_spec if all(k in reference_spec for k in ('front_rise','knee_width','hem_width')) else None)
    result=crewneck(spec,sleeve_basis) if kind=='crewneck' else slacks(spec)
    v,f,_,_=result
    area=np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)
    if not np.isfinite(v).all() or np.any(area<1e-10):
        raise ValueError('Degenerate garment cage; check measurements')
    return result
