# 역할: SAM 표시 메시를 보존하고 의류 주변 계산용 메시만 선택·단순화합니다.
import math

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from core.cloth_geometry import PROXY_ERROR, region_bounds, select_region


def surface_samples(vertices, faces):
    yield from vertices
    edges=set()
    for face in faces:
        yield sum((vertices[i] for i in face),Vector())/len(face)
        for a,b in zip(face,face[1:]+face[:1]): edges.add(tuple(sorted((a,b))))
    for a,b in edges: yield (vertices[a]+vertices[b])*.5


def sampled_error(vertices, faces, tree):
    maximum=0.
    for point in surface_samples(vertices,faces):
        nearest,_,_,distance=tree.find_nearest(point)
        if nearest is None or not math.isfinite(distance): return float('inf')
        maximum=max(maximum,distance)
    return maximum


def build_proxy(vertices, faces, cloth_points):
    bounds=region_bounds(cloth_points)
    selected_vertices,selected_faces=select_region(vertices,faces,bounds)
    selected_vertices=[Vector(p) for p in selected_vertices]
    original_tree=BVHTree.FromPolygons(selected_vertices,selected_faces,all_triangles=False)
    mesh=bpy.data.meshes.new('FitMeCollisionRegion')
    mesh.from_pydata(selected_vertices,[],selected_faces); mesh.update()
    collider=bpy.data.objects.new('FitMeCollision',mesh)
    bpy.context.collection.objects.link(collider)
    meta={'original_faces':len(faces),'selected_faces':len(selected_faces),
          'region_bounds_m':bounds,'region_margin_m':.20,'max_sampled_error_limit_m':PROXY_ERROR,
          'simplification_accepted':False,'simplification_sampled_error_m':0.,
          'display_mesh_modified':False,'final_validation_surface':'original_full_sam'}
    # Keep all display vertices untouched. Only this independent collision copy
    # receives the modifier, and reject simplification outside the error budget.
    if len(selected_faces) > 1000:
        modifier=collider.modifiers.new('Collision simplification','DECIMATE')
        modifier.ratio=.4
        modifier.use_collapse_triangulate=True
        depsgraph=bpy.context.evaluated_depsgraph_get(); depsgraph.update()
        reduced=bpy.data.meshes.new_from_object(collider.evaluated_get(depsgraph),depsgraph=depsgraph)
        collider.modifiers.remove(modifier)
        reduced_vertices=[v.co.copy() for v in reduced.vertices]
        reduced_faces=[tuple(p.vertices) for p in reduced.polygons]
        error=float('inf')
        if reduced_faces and all(math.isfinite(v) for p in reduced_vertices for v in p):
            reduced_tree=BVHTree.FromPolygons(reduced_vertices,reduced_faces,all_triangles=False)
            error=max(sampled_error(reduced_vertices,reduced_faces,original_tree),
                      sampled_error(selected_vertices,selected_faces,reduced_tree))
            # A close but oppositely facing surface is not an acceptable proxy.
            for face in reduced.polygons:
                centre=sum((reduced_vertices[i] for i in face.vertices),Vector())/len(face.vertices)
                _,normal,_,_=original_tree.find_nearest(centre)
                if normal is None or face.normal.dot(normal) <= 0:
                    error=float('inf'); break
        if error <= PROXY_ERROR and len(reduced_faces) < len(selected_faces):
            collider.data=reduced; bpy.data.meshes.remove(mesh)
            meta.update(simplification_accepted=True,simplification_sampled_error_m=error)
        else:
            bpy.data.meshes.remove(reduced)
            meta['simplification_rejection']='sampled_surface_error_or_normals'
            if math.isfinite(error): meta['rejected_sampled_error_m']=error
    meta['collision_faces']=len(collider.data.polygons)
    collider.modifiers.new('Body collision','COLLISION')
    # Compensate the sampled proxy error with contact thickness, without moving
    # the displayed SAM or resizing the garment. Full SAM is checked at the end.
    collider.collision.thickness_outer=.002+meta['simplification_sampled_error_m']
    collider.collision.thickness_inner=.001
    return collider,meta,bounds
