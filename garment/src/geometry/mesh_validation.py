# 역할: BVH 후보와 실제 삼각형 교차로 옷·신체 및 옷 자체의 손상을 판정합니다.
import time
from mathutils.bvhtree import BVHTree
from core.mesh_quality import mesh_statistics, triangulate, triangle_intersection


def intersections(vertices,triangles,tree,other_vertices,other_triangles,other_tree,*,self_check=False):
    started=time.monotonic(); checked=0; crossings=0; coplanar=0
    pairs=tree.overlap(other_tree)
    complete=True
    for first,second in pairs:
        if self_check and (first >= second or set(triangles[first]) & set(triangles[second])): continue
        if checked >= 100000 or time.monotonic()-started > 3.:
            complete=False; break
        checked+=1
        hit=triangle_intersection([vertices[i] for i in triangles[first]],
                                  [other_vertices[i] for i in other_triangles[second]])
        if hit == 'crossing': crossings+=1
        elif hit == 'coplanar_overlap': coplanar+=1
    return {'crossing_pairs':crossings,'coplanar_pairs':coplanar,'checked_pairs':checked,
            'validation_complete':complete,'adjacent_pairs_excluded':self_check}


def validate_mesh(vertices,polygons,reference=None):
    report=mesh_statistics(vertices,polygons,reference)
    if not report['valid']:
        report.update(self_intersections=None,validation_complete=False,
                      self_intersection_check='skipped_invalid_geometry')
        return report
    triangles=triangulate(polygons)
    tree=BVHTree.FromPolygons(vertices,triangles,all_triangles=True)
    overlap=intersections(vertices,triangles,tree,vertices,triangles,tree,self_check=True)
    report.update(self_intersections=overlap['crossing_pairs']+overlap['coplanar_pairs'],
                  validation_complete=overlap['validation_complete'],intersection_check=overlap,
                  self_intersection_check='completed' if overlap['validation_complete'] else 'budget_exceeded')
    if report['self_intersections']: report['reasons'].append('self_intersection')
    if not report['validation_complete']: report['reasons'].append('validation_incomplete')
    report['valid']=not report['reasons']
    return report


class BodySurface:
    def __init__(self,vertices,polygons):
        self.vertices=vertices; self.triangles=triangulate(polygons)
        self.tree=BVHTree.FromPolygons(vertices,self.triangles,all_triangles=True)

    def find_nearest(self,point): return self.tree.find_nearest(point)

    def intersections(self,vertices,polygons):
        triangles=triangulate(polygons)
        tree=BVHTree.FromPolygons(vertices,triangles,all_triangles=True)
        return intersections(vertices,triangles,tree,self.vertices,self.triangles,self.tree)
