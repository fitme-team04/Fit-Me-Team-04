# 역할: DB 원형의 실제 근접 삼각형을 찾아 Cloth 자기 충돌을 안전하게 설정합니다.
import math
import time

from mathutils import Vector
from mathutils.geometry import closest_point_on_tri, intersect_ray_tri
from mathutils.kdtree import KDTree

from core.cloth_resolution import self_collision_exclusions


class _SetupIncomplete(ValueError):
    pass


def _clamp(value):
    return max(0.,min(1.,value))


def _segment_distance_sq(p1,q1,p2,q2):
    d1=q1-p1; d2=q2-p2; r=p1-p2
    a=d1.dot(d1); e=d2.dot(d2); f=d2.dot(r)
    if a <= 1e-24 and e <= 1e-24: return r.dot(r)
    if a <= 1e-24: s=0.; t=_clamp(f/e)
    else:
        c=d1.dot(r)
        if e <= 1e-24: t=0.; s=_clamp(-c/a)
        else:
            b=d1.dot(d2); denominator=a*e-b*b
            s=_clamp((b*f-c*e)/denominator) if denominator > 1e-12*a*e else 0.
            t=(b*s+f)/e
            if t < 0.: t=0.; s=_clamp(-c/a)
            elif t > 1.: t=1.; s=_clamp((b-c)/a)
    delta=(p1+s*d1)-(p2+t*d2)
    return max(0.,delta.dot(delta))


def _triangle_distance_sq(first,second):
    best=min((point-closest_point_on_tri(point,*triangle)).length_squared
             for vertices,triangle in ((first,second),(second,first)) for point in vertices)
    for i in range(3):
        for j in range(3):
            best=min(best,_segment_distance_sq(first[i],first[(i+1)%3],second[j],second[(j+1)%3]))
    # Interior edge/face crossings are not covered by endpoint/edge distances.
    for vertices,triangle in ((first,second),(second,first)):
        for i in range(3):
            start=vertices[i]; direction=vertices[(i+1)%3]-start
            hit=intersect_ray_tri(*triangle,direction,start,True)
            if hit is not None and 0. <= (hit-start).dot(direction) <= direction.length_squared:
                return 0.
    if not math.isfinite(best): raise ValueError('Non-finite cloth contact distance')
    return best


def configure_self_collision(obj, db_rest, edges, polygons, settings, *, distance_m=.001,
                             max_pairs=100000, timeout_seconds=5.,reference_name='original_db_shape'):
    """Exclude only incompatible rest contacts; return an incomplete report on failure.

    KDTree sphere bounds and AABB gaps conservatively cover proximity pairs.
    BVHTree epsilon is deliberately unused: overlap() did not expand its pairs.
    """
    started=time.monotonic()
    report={'configured':False,'validation_complete':False,'source':reference_name,
            'broad_phase':'centroid_spheres_and_aabb','candidate_pairs':0,'near_rest_pairs':0}
    def budget():
        if time.monotonic()-started >= timeout_seconds:
            raise _SetupIncomplete('self_collision_setup_timeout')
    try:
        if type(max_pairs) is not int or max_pairs <= 0 or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError('Invalid cloth contact search budget')
        self_collision_exclusions(db_rest,edges,polygons,distance_m)
        if len(db_rest) != len(obj.data.vertices): raise ValueError('Cloth contact vertex count mismatch')
        settings.self_distance_min=distance_m
        distance_m=float(settings.self_distance_min)
        report['applied_self_distance_m']=distance_m
        base=self_collision_exclusions(db_rest,edges,polygons,distance_m)
        report.update({key:value for key,value in base.items() if key != 'vertices'})
        report['excluded_vertices']=len(base['vertices'])
        points=[Vector(point) for point in db_rest]
        triangles=[]; owners=[]; index_sets=[]
        for face_index,face in enumerate(polygons):
            for i in range(1,len(face)-1):
                indices=(face[0],face[i],face[i+1]); triangle=[points[j] for j in indices]
                if (triangle[1]-triangle[0]).cross(triangle[2]-triangle[0]).length <= 2e-12:
                    raise ValueError('Degenerate cloth contact triangle')
                triangles.append(triangle); owners.append(face_index); index_sets.append(set(indices))
        report['triangles']=len(triangles)
        centers=[sum(triangle,Vector())/3 for triangle in triangles]
        radii=[max((point-center).length for point in triangle) for triangle,center in zip(triangles,centers)]
        lower=[tuple(min(point[k] for point in triangle) for k in range(3)) for triangle in triangles]
        upper=[tuple(max(point[k] for point in triangle) for k in range(3)) for triangle in triangles]
        kd=KDTree(len(triangles))
        for i,center in enumerate(centers): kd.insert(center,i)
        kd.balance(); maximum=max(radii); diameter=2*distance_m; near_faces=set()
        budget()
        for a,center in enumerate(centers):
            budget()
            for _,b,separation in kd.find_range(center,radii[a]+maximum+diameter):
                if a >= b or separation > radii[a]+radii[b]+diameter or index_sets[a].intersection(index_sets[b]): continue
                if any(lower[a][k]-upper[b][k] > diameter or lower[b][k]-upper[a][k] > diameter for k in range(3)): continue
                budget()
                if report['candidate_pairs'] >= max_pairs:
                    raise _SetupIncomplete('self_collision_setup_pair_limit')
                report['candidate_pairs']+=1
                if _triangle_distance_sq(triangles[a],triangles[b]) < diameter*diameter:
                    near_faces.update((owners[a],owners[b])); report['near_rest_pairs']+=1
        policy=self_collision_exclusions(db_rest,edges,polygons,distance_m,near_faces=near_faces)
        report.update({key:value for key,value in policy.items() if key != 'vertices'})
        report['excluded_vertices']=len(policy['vertices'])
        budget()
        if policy['vertices']:
            group=obj.vertex_groups.new(name='FitMeDenseSelfContact')
            group.add(policy['vertices'],1.,'REPLACE')
            settings.vertex_group_self_collisions=group.name
        settings.use_self_collision=True
        settings.self_distance_min=distance_m
        report.update(configured=True,validation_complete=True,
                      applied_self_distance_m=float(settings.self_distance_min))
    except _SetupIncomplete as exc:
        report['reason']=str(exc)
    except (ValueError,TypeError,IndexError,OverflowError) as exc:
        report.update(reason='invalid_self_collision_rest',detail=str(exc))
    report['setup_seconds']=time.monotonic()-started
    return report
