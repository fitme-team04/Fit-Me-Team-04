# 역할: 옷 메시의 퇴화·토폴로지와 실제 삼각형 교차를 검사합니다.
import math
from collections import Counter

EPS = 1e-8


def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def norm(a): return math.sqrt(dot(a,a))


def triangulate(polygons):
    return [(face[0],face[i],face[i+1]) for face in polygons for i in range(1,len(face)-1)]


def triangle_area(points):
    a,b,c=points
    return norm(cross(sub(b,a),sub(c,a)))/2


def segment_crosses_triangle(start,end,triangle):
    a,b,c=triangle; direction=sub(end,start); e1=sub(b,a); e2=sub(c,a)
    h=cross(direction,e2); determinant=dot(e1,h)
    if abs(determinant) <= 1e-12*max(norm(e1)*norm(h),1e-20): return False
    inv=1/determinant; s=sub(start,a); u=inv*dot(s,h)
    q=cross(s,e1); v=inv*dot(direction,q); amount=inv*dot(e2,q)
    return EPS < amount < 1-EPS and u >= -EPS and v >= -EPS and u+v <= 1+EPS


def triangle_intersection(first,second):
    """Return crossing/coplanar_overlap; shared-edge or point contact is allowed."""
    n1=cross(sub(first[1],first[0]),sub(first[2],first[0]))
    n2=cross(sub(second[1],second[0]),sub(second[2],second[0]))
    l1,l2=norm(n1),norm(n2)
    if min(l1,l2) < 1e-14: return None
    d1=[dot(n1,sub(p,first[0]))/l1 for p in second]
    d2=[dot(n2,sub(p,second[0]))/l2 for p in first]
    if max(abs(v) for v in (*d1,*d2)) <= EPS:
        axis=max(range(3),key=lambda i:abs(n1[i]))
        def project(triangle): return [tuple(p[i] for i in range(3) if i != axis) for p in triangle]
        a,b=project(first),project(second)
        for triangle in (a,b):
            for p,q in zip(triangle,triangle[1:]+triangle[:1]):
                edge=sub(q,p); normal=(-edge[1],edge[0]); length=norm(normal)
                if length < 1e-14: continue
                pa=[dot(p,normal)/length for p in a]; pb=[dot(p,normal)/length for p in b]
                if min(max(pa),max(pb))-max(min(pa),min(pb)) <= EPS: return None
        return 'coplanar_overlap'
    if min(d1) >= -EPS or max(d1) <= EPS or min(d2) >= -EPS or max(d2) <= EPS:
        return None
    for a,b in ((first,second),(second,first)):
        if any(segment_crosses_triangle(p,q,b) for p,q in zip(a,a[1:]+a[:1])):
            return 'crossing'
    return None


def mesh_statistics(vertices,polygons,reference=None):
    if not vertices or any(len(p) != 3 or any(not math.isfinite(v) for v in p) for p in vertices):
        return {'valid':False,'reasons':['non_finite_vertices'],'degenerate_triangles':0}
    if any(len(face) < 3 or any(i < 0 or i >= len(vertices) for i in face) for face in polygons):
        return {'valid':False,'reasons':['invalid_face_indices'],'degenerate_triangles':0}
    triangles=triangulate(polygons); edges=Counter(); duplicates=Counter()
    for face in polygons:
        duplicates[tuple(sorted(face))]+=1
        for a,b in zip(face,face[1:]+face[:1]): edges[tuple(sorted((a,b)))]+=1
    degenerate=0; skinny=0; degraded=0; worst_aspect=0.; minimum_ratio=1.
    worst_aspect_change=1.
    for tri in triangles:
        points=[vertices[i] for i in tri]; area=triangle_area(points)
        if reference is not None:
            rest_area=triangle_area([reference[i] for i in tri])
            ratio=area/rest_area if rest_area > 1e-14 else 0.
            minimum_ratio=min(minimum_ratio,ratio)
        else: ratio=1.
        longest=max(norm(sub(a,b)) for a,b in zip(points,points[1:]+points[:1]))
        aspect=longest*longest/max(2*area,1e-30)
        worst_aspect=max(worst_aspect,aspect)
        if aspect > 1000: skinny+=1
        if reference is not None:
            reference_points=[reference[i] for i in tri]
            reference_longest=max(norm(sub(a,b)) for a,b in zip(reference_points,reference_points[1:]+reference_points[:1]))
            reference_aspect=reference_longest**2/max(2*rest_area,1e-30)
            aspect_change=aspect/max(reference_aspect,1e-30)
            worst_aspect_change=max(worst_aspect_change,aspect_change)
            if aspect > 1000 and aspect_change > 10: degraded+=1
        # A thin source triangle is a conditioning warning, not zero area.
        # Preserve topology/binding and fail true collapse or new severe damage.
        if area < 1e-12 or ratio < .02: degenerate+=1
    reasons=[]
    if not triangles: reasons.append('no_faces')
    if degenerate: reasons.append('degenerate_faces')
    if degraded: reasons.append('triangle_shape_degraded')
    if any(n > 2 for n in edges.values()): reasons.append('non_manifold_edges')
    if any(n > 1 for n in duplicates.values()): reasons.append('duplicate_faces')
    return {'valid':not reasons,'reasons':reasons,'vertex_count':len(vertices),'triangle_count':len(triangles),
            'degenerate_triangles':degenerate,'worst_triangle_aspect':worst_aspect,
            'skinny_triangles':skinny,'shape_degraded_triangles':degraded,
            'worst_triangle_aspect_change':worst_aspect_change,
            'warnings':['skinny_triangles'] if skinny else [],
            'min_triangle_area_ratio':minimum_ratio,
            'bounds_m':{'min':[min(p[i] for p in vertices) for i in range(3)],
                        'max':[max(p[i] for p in vertices) for i in range(3)]}}
