# 역할: 기준 신체와의 대응을 이용해 의류를 새 체형으로 이동시키고, 검증 실패한 관통 의류 출력을 차단합니다.
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def bind_body(garment_vertices, body_vertices, body_faces):
    tree=BVHTree.FromPolygons(body_vertices.tolist(),body_faces.tolist(),all_triangles=True)
    ids=[];weights=[]
    for point in garment_vertices:
        closest,_,index,_=tree.find_nearest(Vector(point))
        triangle=body_faces[index];a,b,c=body_vertices[triangle]
        uv=np.linalg.lstsq(np.column_stack((b-a,c-a)),np.asarray(closest)-a,rcond=None)[0]
        weight=np.clip([1-uv.sum(),uv[0],uv[1]],0,1);weight/=weight.sum()
        ids.append(triangle);weights.append(weight)
    return np.asarray(ids),np.asarray(weights)


def follow_body(vertices, reference_body, target_body, ids, weights):
    if reference_body.shape!=target_body.shape:
        raise ValueError('Body topology does not match the registered reference')
    result=vertices+np.einsum('vij,vi->vj',(target_body-reference_body)[ids],weights)
    if not np.isfinite(result).all():raise ValueError('Non-finite body-follow result')
    return result


def require_clear(report):
    if report['body_triangle_intersections'] or any(report[key]['inside'] for key in ('vertices','edge_midpoints','triangle_centroids')):
        raise ValueError('Garment still intersects body; output blocked')
    if report['topology']['degenerate_triangles'] or report['topology']['nonmanifold_edges_gt2']:
        raise ValueError('Garment topology invalid after correction; output blocked')
