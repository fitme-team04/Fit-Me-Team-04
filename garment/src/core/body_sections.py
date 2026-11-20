# 역할: SAM 평면 단면의 닫힌 윤곽을 분리하고 몸통·팔에 해당하는 윤곽만 선택합니다.
import math

import numpy as np


def _geometry(vertices, triangles):
    try:
        points=np.asarray(vertices,dtype=float)
        faces=np.asarray(triangles)
    except (TypeError,ValueError,OverflowError) as exc:
        raise ValueError('Invalid body section input') from exc
    if (points.ndim!=2 or points.shape[1]!=3 or not len(points)
            or not np.isfinite(points).all()):
        raise ValueError('Invalid body section vertices')
    if (faces.ndim!=2 or faces.shape[1]!=3 or faces.dtype.kind not in 'iu'
            or np.any(faces<0) or np.any(faces>=len(points))
            or np.any(faces[:,0]==faces[:,1]) or np.any(faces[:,1]==faces[:,2])
            or np.any(faces[:,2]==faces[:,0])):
        raise ValueError('Invalid body section triangles')
    return points,faces


def _vector(value,label):
    try:
        result=np.asarray(value,dtype=float)
    except (TypeError,ValueError,OverflowError) as exc:
        raise ValueError('Invalid '+label) from exc
    if result.shape!=(3,) or not np.isfinite(result).all():
        raise ValueError('Invalid '+label)
    return result


def _plane(origin,normal):
    origin=_vector(origin,'body section origin')
    normal=_vector(normal,'body section axis')
    length=math.hypot(*normal)
    if not math.isfinite(length) or length<1e-12:
        raise ValueError('Degenerate body section axis')
    normal=normal/length
    reference=np.zeros(3);reference[int(np.argmin(np.abs(normal)))]=1.
    first=np.cross(normal,reference);first/=np.linalg.norm(first)
    second=np.cross(normal,first)
    return origin,normal,np.column_stack((first,second))


def _area_centroid(loop):
    x,y=loop[:,0],loop[:,1]
    next_x,next_y=np.roll(x,-1),np.roll(y,-1)
    cross=x*next_y-next_x*y
    double_area=float(np.sum(cross))
    if abs(double_area)<=1e-16:
        return 0.,loop[:,:2].mean(axis=0)
    centroid=np.array([np.sum((x+next_x)*cross),np.sum((y+next_y)*cross)])/(3*double_area)
    return abs(double_area)/2,centroid


def plane_contours(vertices, triangles, origin, normal):
    """Return separate ordered closed Nx3 contours, without joining limb loops.

    The last point is not repeated. Open/non-manifold cut components are omitted.
    A plane coincident with mesh vertices can produce no valid closed contour;
    callers may try a nearby height rather than merging disconnected components.
    """
    points,faces=_geometry(vertices,triangles)
    origin,normal,basis=_plane(origin,normal)
    distance=(points-origin)@normal
    signs=distance[faces]>0
    cuts=faces[signs.any(axis=1)&~signs.all(axis=1)]
    graph={}
    for triangle in cuts:
        ends=[]
        for a,b in zip(triangle,np.roll(triangle,1)):
            if (distance[a]>0)!=(distance[b]>0):
                ends.append(tuple(sorted((int(a),int(b)))))
        if len(ends)!=2: continue
        a,b=ends
        graph.setdefault(a,[]).append(b)
        graph.setdefault(b,[]).append(a)
    remaining=set(graph);result=[]
    tolerance=max(1.,float(np.max(np.abs(points))))*1e-12
    while remaining:
        start=min(remaining);stack=[start];component=set()
        while stack:
            current=stack.pop()
            if current in component: continue
            component.add(current);remaining.discard(current)
            stack.extend(neighbor for neighbor in graph[current] if neighbor not in component)
        if any(len(graph[node])!=2 for node in component): continue
        ordered=[];previous=None;current=start
        while current not in ordered:
            ordered.append(current)
            neighbors=graph[current]
            following=neighbors[0] if neighbors[0]!=previous else neighbors[1]
            previous,current=current,following
        if current!=start or len(ordered)!=len(component) or len(ordered)<3: continue
        edges=np.asarray(ordered,dtype=int);a,b=edges.T
        amount=distance[a]/(distance[a]-distance[b])
        loop=points[a]+amount[:,None]*(points[b]-points[a])
        # Coplanar endpoint hits may repeat the same position on two source edges.
        keep=np.linalg.norm(loop-np.roll(loop,1,axis=0),axis=1)>tolerance
        loop=loop[keep]
        if len(loop)>=3 and _area_centroid((loop-origin)@basis)[0]>tolerance*tolerance:
            result.append(loop)
    return result


def horizontal_contours(vertices, triangles, z):
    """Return separate closed contours on the horizontal plane at z."""
    try:
        level=float(z)
    except (TypeError,ValueError,OverflowError) as exc:
        raise ValueError('Invalid body section height') from exc
    if not math.isfinite(level):raise ValueError('Invalid body section height')
    return plane_contours(vertices,triangles,(0.,0.,level),(0.,0.,1.))


def torso_contour(vertices, triangles, z, center_x=0., center_y=None):
    """Select one centre-straddling torso contour, never a combined bounding box.

    Without a Y guide the largest projected area wins, excluding a small hand
    crossing the centreline. With a guide, choose the closest area centroid.
    """
    try:
        center_x=float(center_x)
        center_y=None if center_y is None else float(center_y)
    except (TypeError,ValueError,OverflowError) as exc:
        raise ValueError('Invalid torso section guide') from exc
    if not math.isfinite(center_x) or (center_y is not None and not math.isfinite(center_y)):
        raise ValueError('Invalid torso section guide')
    candidates=[]
    for loop in horizontal_contours(vertices,triangles,z):
        if not float(loop[:,0].min())<center_x<float(loop[:,0].max()): continue
        area,centroid=_area_centroid(loop)
        rank=(-area,) if center_y is None else (float(np.linalg.norm(centroid-[center_x,center_y])),-area)
        candidates.append((rank,loop))
    if not candidates: raise ValueError('No isolated closed SAM torso contour at this height')
    return min(candidates,key=lambda item:item[0])[1]


def _contains_origin(loop,tolerance):
    inside=False
    for a,b in zip(loop,np.roll(loop,-1,axis=0)):
        direction=b-a;length_sq=float(direction@direction)
        amount=max(0.,min(1.,-float(a@direction)/length_sq)) if length_sq>0 else 0.
        if float(np.linalg.norm(a+amount*direction))<=tolerance:return True
        if (a[1]>0)!=(b[1]>0):
            x=float(a[0]-a[1]*(b[0]-a[0])/(b[1]-a[1]))
            if x>0:inside=not inside
    return inside


def arm_contour(vertices, triangles, origin, axis, *, max_radius=None):
    """Select a closed section perpendicular to the actual SAM arm axis.

    Origin-containing contours take priority, then the nearest area centroid.
    max_radius bounds every contour point's radial distance from the arm axis;
    it rejects oversized shoulder/torso joins rather than inventing an arm size.
    Missing suitable sections raise ValueError for the caller to interpolate
    from independently valid distal arm sections.
    """
    origin,normal,basis=_plane(origin,axis)
    if max_radius is not None:
        try:max_radius=float(max_radius)
        except (TypeError,ValueError,OverflowError) as exc:
            raise ValueError('Invalid arm section radius limit') from exc
        if not math.isfinite(max_radius) or max_radius<=0:
            raise ValueError('Invalid arm section radius limit')
    candidates=[]
    for loop in plane_contours(vertices,triangles,origin,normal):
        projected=(loop-origin)@basis
        radii=np.linalg.norm(projected,axis=1)
        if max_radius is not None and float(np.max(radii))>max_radius:continue
        area,centroid=_area_centroid(projected)
        tolerance=max(1.,float(np.max(radii)))*1e-10
        rank=(not _contains_origin(projected,tolerance),float(np.linalg.norm(centroid)),-area)
        candidates.append((rank,loop))
    if not candidates:raise ValueError('No isolated closed SAM arm contour within radius limit')
    return min(candidates,key=lambda item:item[0])[1]
