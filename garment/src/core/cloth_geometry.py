# 역할: 충돌 영역 선택과 DB 기준 국소 보정의 변형 한계를 검사합니다.
"""Geometry policy independent of Blender, with metre coordinates."""
import math
import time
from core.cloth_contract import MAX_EDGE_STRETCH

REGION_MARGIN = .20
PROXY_ERROR = .002
PUSH_DEPTH = .005
PUSH_OFFSET = .002
PUSH_DISPLACEMENT = .008


def region_bounds(points, margin=REGION_MARGIN):
    if not points or not math.isfinite(margin) or margin <= 0:
        raise ValueError('Invalid collision region')
    return ([min(p[i] for p in points)-margin for i in range(3)],
            [max(p[i] for p in points)+margin for i in range(3)])


def inside_region(points, bounds):
    low,high=bounds
    return all(all(low[i] <= p[i] <= high[i] for i in range(3)) for p in points)


def select_region(vertices, faces, bounds):
    low,high=bounds
    selected=[]
    for face in faces:
        # Include crossing triangles even if none of their vertices is in the box.
        if all(max(vertices[j][axis] for j in face) >= low[axis] and
               min(vertices[j][axis] for j in face) <= high[axis] for axis in range(3)):
            selected.append(face)
    if not selected:
        raise ValueError('No SAM faces in garment collision region')
    used=sorted({i for face in selected for i in face})
    mapping={old:new for new,old in enumerate(used)}
    return [vertices[i] for i in used], [tuple(mapping[i] for i in face) for face in selected]


def length(a,b):
    return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))


def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def relax_contacts(points, edges, reference, nearest, iterations=40):
    """Spread contact correction through neighbors while retaining DB spring lengths.

    This is a bounded initial placement, never a new spring reference. The caller
    must check triangle crossings and mesh quality before starting Blender Cloth.
    """
    original=[tuple(p) for p in points]; current=list(original)
    lengths=[length(reference[a],reference[b]) for a,b in edges]
    if not edges or any(v <= 1e-10 for v in lengths):
        raise ValueError('Invalid contact relaxation edges')
    started=time.monotonic(); completed=0
    for _ in range(iterations):
        if time.monotonic()-started >= 5.: break
        for i,p in enumerate(current):
            surface,normal=nearest(p)
            if surface is None or normal is None: raise ValueError('Missing SAM relaxation contact')
            if any(not math.isfinite(v) for item in (surface,normal) for v in item):
                raise ValueError('Non-finite SAM relaxation contact')
            signed=sum((p[k]-surface[k])*normal[k] for k in range(3))
            if signed < .004:
                current[i]=tuple(p[k]+normal[k]*min(.01,.004-signed) for k in range(3))
        # Project onto original DB edge lengths instead of moving isolated
        # vertices and rejecting their stretched neighboring edges immediately.
        for _ in range(8):
            for (a,b),target in zip(edges,lengths):
                delta=tuple(current[b][k]-current[a][k] for k in range(3))
                distance=math.sqrt(sum(v*v for v in delta))
                if distance < 1e-12: continue
                correction=tuple(v*(distance-target)/(2*distance) for v in delta)
                current[a]=tuple(current[a][k]+correction[k] for k in range(3))
                current[b]=tuple(current[b][k]-correction[k] for k in range(3))
        for i,p in enumerate(current):
            displacement=length(p,original[i])
            if displacement > .06:
                current[i]=tuple(original[i][k]+(p[k]-original[i][k])*.06/displacement for k in range(3))
        completed+=1
    ratios=[length(current[a],current[b])/target for (a,b),target in zip(edges,lengths)]
    finite=all(math.isfinite(v) for p in current for v in p)
    accepted=finite and min(ratios) >= .98 and max(ratios) <= MAX_EDGE_STRETCH
    return current if accepted else original, {
        'accepted':accepted,'iterations':completed,'time_budget_exhausted':completed < iterations,
        'min_edge_ratio':min(ratios),
        'max_edge_ratio':max(ratios),'displacement_limit_m':.06,
        'max_displacement_m':max(length(p,q) for p,q in zip(current,original))}


def push_out(points, edges, polygons, nearest, passes=3):
    """Move only shallow interior vertices; rollback any DB-size/face violation.

    nearest(point) returns (surface_position, outward_normal). It must use the
    full-resolution original SAM, never the cropped/decimated proxy.
    """
    original=[tuple(p) for p in points]
    if any(len(p) != 3 or any(not math.isfinite(v) for v in p) for p in original):
        raise ValueError('Invalid DB cloth positions')
    current=list(original)
    moved=set()
    deepest=0.
    for _ in range(passes):
        changed=False
        for index,point in enumerate(current):
            surface,normal=nearest(point)
            if surface is None or normal is None:
                raise ValueError('Missing original SAM contact')
            if any(not math.isfinite(v) for p in (surface,normal) for v in p):
                raise ValueError('Non-finite SAM contact')
            signed=sum((point[i]-surface[i])*normal[i] for i in range(3))
            if signed >= -.0001:
                continue
            deepest=max(deepest,-signed)
            if -signed > PUSH_DEPTH:
                continue
            proposed=tuple(surface[i]+normal[i]*PUSH_OFFSET for i in range(3))
            if length(proposed,original[index]) > PUSH_DISPLACEMENT:
                continue
            current[index]=proposed; moved.add(index); changed=True
        if not changed: break
    ratios=[]
    for a,b in edges:
        old=length(original[a],original[b])
        if old <= 0: raise ValueError('Degenerate DB cloth edge')
        ratios.append(length(current[a],current[b])/old)
    flipped=False
    for face in polygons:
        # Check every fan triangle, not just the first three vertices of a quad.
        for i in range(1,len(face)-1):
            a,b,c=face[0],face[i],face[i+1]
            def normal(values):
                return cross(tuple(values[b][j]-values[a][j] for j in range(3)),
                             tuple(values[c][j]-values[a][j] for j in range(3)))
            before,after=normal(original),normal(current)
            if sum(a*b for a,b in zip(before,after)) <= 0:
                flipped=True
    accepted=bool(ratios) and max(ratios) <= MAX_EDGE_STRETCH and min(ratios) >= .98 and not flipped
    report={'accepted':accepted,'attempted_vertices':len(moved),
            'moved_vertices':len(moved) if accepted else 0,'max_detected_depth_m':deepest,
            'attempted_max_edge_ratio':max(ratios,default=1.),
            'attempted_min_edge_ratio':min(ratios,default=1.),'face_flip_detected':flipped,
            'attempted_max_displacement_m':max((length(a,b) for a,b in zip(original,current)),default=0.)}
    return current if accepted else original, report
