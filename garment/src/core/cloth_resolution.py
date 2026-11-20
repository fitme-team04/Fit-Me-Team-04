# 역할: 계산 메시 해상도보다 두꺼운 자기 충돌이 정지 상태의 옷을 밀어내지 않도록 제외 영역을 찾습니다.
import math
from numbers import Integral


def self_collision_exclusions(points, edges, polygons, distance_m=.001, *, near_faces=()):
    if not isinstance(distance_m,(int,float)) or isinstance(distance_m,bool) or not math.isfinite(distance_m) or distance_m <= 0:
        raise ValueError('Invalid cloth self collision distance')
    try:
        if not len(points) or any(len(p) != 3 or any(not math.isfinite(v) for v in p) for p in points):
            raise ValueError('Invalid cloth rest vertices')
        def indices(item, minimum):
            return len(item) >= minimum and all(isinstance(i,Integral) and not isinstance(i,bool)
                and 0 <= i < len(points) for i in item) and len(set(item)) == len(item)
        if not len(edges) or any(len(edge) != 2 or not indices(edge,2) for edge in edges):
            raise ValueError('Invalid cloth rest edges')
        if not len(polygons) or any(not indices(face,3) for face in polygons):
            raise ValueError('Invalid cloth rest faces')
        near_faces=set(near_faces)
        if any(not isinstance(i,Integral) or isinstance(i,bool) or not 0 <= i < len(polygons) for i in near_faces):
            raise ValueError('Invalid near-contact face indices')
    except (TypeError,IndexError,OverflowError) as exc:
        raise ValueError('Invalid cloth self collision geometry') from exc
    lengths=[math.dist(points[a],points[b]) for a,b in edges]
    if not lengths or any(not math.isfinite(v) or v <= 0 for v in lengths):
        raise ValueError('Invalid cloth mesh edges')
    # Two nonadjacent faces in a densely tessellated neck/cuff can lie within
    # twice the contact radius even at rest. Exclude the affected patch, keeping
    # self collision on the rest of the garment and exact final checks on all faces.
    short={i for (a,b),length in zip(edges,lengths) if length < 2*distance_m for i in (a,b)}
    dense=set(short)
    altitude_faces=0
    # A long, narrow triangle can have no short edge while its opposite sides
    # are closer than the contact diameter. Use the same fan as the geometry
    # search, then expand its polygon vertices by one incident-face ring.
    for face in polygons:
        narrow=False
        for i in range(1,len(face)-1):
            a,b,c=(points[j] for j in (face[0],face[i],face[i+1]))
            ab=tuple(y-x for x,y in zip(a,b)); ac=tuple(y-x for x,y in zip(a,c))
            normal=(ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0])
            longest=max(math.dist(a,b),math.dist(b,c),math.dist(c,a))
            altitude=math.hypot(*normal)/longest if longest > 0 else 0.
            if not math.isfinite(altitude): raise ValueError('Non-finite cloth triangle altitude')
            if altitude < 2*distance_m: narrow=True
        if narrow:
            altitude_faces+=1
            dense.update(face)
    vertices=set(dense)
    for face in polygons:
        if dense.intersection(face): vertices.update(face)
    # Geometry-specific proximity search supplies polygon IDs; this core policy
    # stays independent of Blender and never changes material coordinates.
    for index in near_faces: vertices.update(polygons[index])
    excluded_faces=sum(all(i in vertices for i in face) for face in polygons)
    return {'vertices':sorted(vertices),'excluded_faces':excluded_faces,
            'min_edge_m':min(lengths),'self_distance_m':distance_m,
            'near_rest_faces':len(near_faces),'short_edge_seed_vertices':len(short),
            'altitude_seed_faces':altitude_faces,
            'reason':'rest_neighborhood_below_contact_diameter' if vertices else None}
