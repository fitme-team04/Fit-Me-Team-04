# 역할: 관통 보정이 수렴하지 않는 삼각형만 세분화해 UV를 유지하며 다시 투영합니다.
import bmesh
import numpy as np
from mathutils import Vector
from fit_uploaded_garments import shell_clearances
from rebuild_cc0_reference import clear_body,tree
from geometry.template_binding import geometry


def project_surface(obj,vertices,faces,body,body_faces,targets,protect_feet=False):
    initial=vertices.copy()
    # Excess trouser length cannot continue below the floor through the foot.
    # Lift only low points over the instep; preserve a small monotonic Z spread.
    floor=float(body[:,2].min())
    if protect_feet or vertices[:,2].min()<floor-.001:
        vertices=vertices.copy();limit=floor+float(np.ptp(body[:,2]))*.14
        foot_faces=body_faces[body[body_faces,2].max(axis=1)<limit]
        foot=tree(body,foot_faces);minimum=float(vertices[:,2].min())
        for index in np.flatnonzero(vertices[:,2]<limit):
            x,y,z=vertices[index]
            hit,_,_,_=foot.ray_cast(Vector((x,y,limit+.01)),Vector((0,0,-1)),limit-floor+.5)
            if hit is not None and z<hit.z+.006:
                vertices[index,2]=hit.z+.006+.01*(z-minimum)
    corrected,iterations=clear_body(vertices,faces,body,body_faces,minimum_clearance=.0012,vertex_clearance=targets,max_iterations=8)
    reference=initial.copy()
    for _ in range(5):
        pairs=tree(corrected,faces).overlap(tree(body,body_faces))
        if not pairs:break
        obj.data.vertices.foreach_set('co',corrected.ravel());obj.data.update();obj.data.calc_loop_triangles()
        polygons={obj.data.loop_triangles[i].polygon_index for i,_ in pairs}
        bm=bmesh.new();bm.from_mesh(obj.data);bm.faces.ensure_lookup_table();bm.verts.ensure_lookup_table()
        layer=bm.verts.layers.float_vector.get('FitMeUnprojected') or bm.verts.layers.float_vector.new('FitMeUnprojected')
        for index,vertex in enumerate(bm.verts):vertex[layer]=reference[index]
        bmesh.ops.subdivide_edges(bm,edges=list({e for i in polygons for e in bm.faces[i].edges}),cuts=1,use_grid_fill=True)
        bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.verts.index_update()
        reference=np.array([v[layer][:] for v in bm.verts])
        bm.to_mesh(obj.data);bm.free();obj.data.update()
        corrected,faces=geometry(obj)
        targets=shell_clearances(corrected,faces,body,body_faces)
        corrected,extra=clear_body(corrected,faces,body,body_faces,minimum_clearance=.0012,vertex_clearance=targets,max_iterations=4)
        iterations+=extra
    return corrected,faces,iterations,float(np.linalg.norm(corrected-reference,axis=1).max()*100)
