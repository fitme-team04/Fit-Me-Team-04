# 역할: 의류·신체 자세 차이와 초기 피팅의 치수 보존을 검사합니다.
import math
from collections import Counter

from core.cloth_contract import MAX_EDGE_STRETCH
from core.cloth_geometry import cross, length


def direction(a,b):
    d=tuple(y-x for x,y in zip(a,b)); n=math.sqrt(sum(v*v for v in d))
    if n < 1e-8: raise ValueError('Coincident fitting landmarks')
    return tuple(v/n for v in d)


def angle_degrees(a,b):
    ua=direction((0,0,0),a); ub=direction((0,0,0),b)
    return math.degrees(math.acos(max(-1.,min(1.,sum(x*y for x,y in zip(ua,ub))))))


def sleeve_target_on_arm(garment_shoulder, garment_cuff, body_shoulder, body_wrist):
    """Meet the body arm segment by rotating a sleeve of unchanged length."""
    points=[]
    try:
        for point in (garment_shoulder,garment_cuff,body_shoulder,body_wrist):
            values=tuple(point)
            if len(values) != 3 or any(isinstance(v,(bool,str,bytes)) for v in values):
                raise ValueError('Invalid sleeve fitting landmarks')
            values=tuple(float(v) for v in values)
            if not all(math.isfinite(v) for v in values):
                raise ValueError('Non-finite sleeve fitting landmarks')
            points.append(values)
    except (TypeError,OverflowError) as exc:
        raise ValueError('Invalid sleeve fitting landmarks') from exc
    shoulder,cuff,body_start,body_end=points
    radius=math.dist(shoulder,cuff)
    arm=tuple(b-a for a,b in zip(body_start,body_end)); arm_length=math.hypot(*arm)
    if not math.isfinite(radius) or not math.isfinite(arm_length) or min(radius,arm_length) < 1e-8:
        raise ValueError('Degenerate sleeve or body arm landmarks')
    axis=tuple(v/arm_length for v in arm)
    offset=tuple(b-a for a,b in zip(shoulder,body_start))
    projection=sum(a*b for a,b in zip(offset,axis))
    perpendicular=math.hypot(*(v-projection*u for v,u in zip(offset,axis)))
    if not math.isfinite(perpendicular) or perpendicular > radius:
        raise ValueError('Sleeve length does not reach body arm')
    # The larger root points toward the wrist. A sleeve which reaches only
    # beyond the wrist or behind the shoulder cannot be fitted by rotation.
    forward=-projection+radius*math.sqrt(max(0.,1-(perpendicular/radius)**2))
    amount=forward/arm_length
    if not math.isfinite(amount) or not 0 <= amount <= 1:
        raise ValueError('Sleeve target lies outside body arm segment')
    return tuple(a+amount*d for a,d in zip(body_start,arm))


def pose_error(source, body):
    """Sleeve angle (degrees), then shoulder landmark distance (meters)."""
    angles=[]; gaps=[]
    for side in ('L','R'):
        shoulder='fit_shoulder_'+side; cuff='fit_cuff_'+side; wrist='fit_wrist_'+side
        if all(key in source for key in (shoulder,cuff)) and all(key in body for key in (shoulder,wrist)):
            angles.append(angle_degrees(tuple(a-b for a,b in zip(source[cuff],source[shoulder])),
                                        tuple(a-b for a,b in zip(body[wrist],body[shoulder]))))
            gaps.append(length(source[shoulder],body[shoulder]))
    return (sum(angles)/len(angles),sum(gaps)/len(gaps)) if angles else (0.,0.)


def translate_landmarks(anchors, shift):
    """Translate glTF anatomical anchors by a Blender-axis rigid displacement."""
    dx,dy,dz=shift
    for anchor in anchors:
        if anchor['name'] in ('fit_anchor','fit_anchor_waist'): continue
        x,y,z=anchor['translation']
        anchor['translation']=[x+dx,y+dz,z-dy]


def neck_registration(garment_necks, body_necks, body_shoulders):
    targets=[]
    for side in ('L','R'):
        g,n,s=garment_necks[side],body_necks[side],body_shoulders[side]
        if abs(s[0]-n[0]) < .01: raise ValueError('Invalid clavicle landmarks')
        amount=(g[0]-n[0])/(s[0]-n[0])
        # Register where the garment neck opening meets the body's shoulder
        # line. Never shrink its neck/shoulder width to the body's width.
        targets.append(tuple(n[i]+amount*(s[i]-n[i])-g[i] for i in range(3)))
    shift=[0.,sum(v[1] for v in targets)/2,sum(v[2] for v in targets)/2]
    if abs(shift[1]) > .04 or abs(shift[2]) > .06:
        raise ValueError('Landmark registration exceeds bounded initial placement')
    return shift


def pose_strain(original, posed, edges, polygons):
    if len(original) != len(posed) or not edges or any(
            not math.isfinite(v) for points in (original,posed) for point in points for v in point):
        raise ValueError('Invalid initial pose vertices')
    if any(length(original[a],original[b]) < 1e-10 for a,b in edges):
        raise ValueError('Degenerate initial pose edge')
    ratios=[length(posed[a],posed[b])/length(original[a],original[b]) for a,b in edges]
    flipped=False
    for face in polygons:
        for i in range(1,len(face)-1):
            a,b,c=face[0],face[i],face[i+1]
            def normal(points):
                return cross(tuple(points[b][j]-points[a][j] for j in range(3)),
                             tuple(points[c][j]-points[a][j] for j in range(3)))
            before,after=normal(original),normal(posed)
            if sum(x*y for x,y in zip(before,after)) <= 0: flipped=True
    low,high=min(ratios),max(ratios)
    return {'accepted':low >= .98 and high <= MAX_EDGE_STRETCH and not flipped,
            'min_edge_ratio':low,'max_edge_ratio':high,'face_flip':flipped}


def orient_closed_surface(vertices, faces):
    edges=Counter(); winding=Counter(); volume=0.
    for face in faces:
        for a,b in zip(face,face[1:]+face[:1]):
            edge=tuple(sorted((a,b))); edges[edge]+=1; winding[edge]+=1 if a<b else -1
        for i in range(1,len(face)-1):
            a,b,c=(vertices[j] for j in (face[0],face[i],face[i+1]))
            bc=cross(b,c); volume+=sum(x*y for x,y in zip(a,bc))/6
    closed=bool(edges) and all(count == 2 for count in edges.values())
    inconsistent=sum(edges[e] == 2 and winding[e] != 0 for e in edges)
    reverse=closed and inconsistent == 0 and volume < -1e-9
    report={'closed_surface':closed,'inconsistent_edges':inconsistent,
            'boundary_edges':sum(n == 1 for n in edges.values()),
            'signed_volume_m3':volume,'reversed_for_collision':reverse}
    return [tuple(reversed(face)) for face in faces] if reverse else faces,report
