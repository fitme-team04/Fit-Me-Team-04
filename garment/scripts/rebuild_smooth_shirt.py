# 역할: 몸통과 소매를 하나의 매끄러운 표면으로 결합하고 배 돌출 없는 윤곽·좁아지는 밑단을 생성합니다.
import argparse,json,sys
from pathlib import Path
import bpy,bmesh
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from geometry.template_binding import geometry
from geometry.body_clearance import require_clear
from prepare_template import register
from rebuild_cc0_reference import vertices_world,triangles,inspect,tree,boundary_loops,clear_body,save_anchor_bindings


def loft(name,rings):
    vertices=np.vstack(rings);n=len(rings[0]);faces=[]
    for row in range(len(rings)-1):
        for i in range(n):faces.append((row*n+i,row*n+(i+1)%n,(row+1)*n+(i+1)%n,(row+1)*n+i))
    faces.append(tuple(reversed(range(n))));faces.append(tuple((len(rings)-1)*n+i for i in range(n)))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices.tolist(),[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    return obj


def connected_components(faces,n):
    graph=[[] for _ in range(n)]
    for a,b,c in faces:
        graph[a].extend((b,c));graph[b].extend((a,c));graph[c].extend((a,b))
    remaining=set(range(n));groups=[]
    while remaining:
        seed=remaining.pop();group={seed};stack=[seed]
        while stack:
            for vertex in graph[stack.pop()]:
                if vertex in remaining:remaining.remove(vertex);group.add(vertex);stack.append(vertex)
        groups.append(group)
    return groups


def main():
    parser=argparse.ArgumentParser()
    for arg in ('models','body','output'):parser.add_argument('--'+arg,type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(args.body.resolve()))
    body_obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    body=vertices_world(body_obj);body_faces=triangles(body_obj)
    anchors={o.name:o.matrix_world.copy() for o in bpy.context.scene.objects if o.name.startswith('fit_')}
    registry=json.loads((args.models/'registry.json').read_text());pants_name,entry=next((n,e) for n,e in registry['templates'].items() if e['kind']=='slacks')
    with bpy.data.libraries.load(str((args.models/entry['blend']).resolve()),link=False) as (src,dst):dst.objects=[entry['object']]
    pants=dst.objects[0];bpy.context.collection.objects.link(pants)
    pants_vertices,pants_faces=geometry(pants)
    pants_world=np.array([anchors['fit_anchor_waist']@Vector(p) for p in pants_vertices])
    theta=np.linspace(0,2*np.pi,96,endpoint=False);circle=np.column_stack((np.cos(theta),np.sin(theta)))
    # Constant front/back depth avoids copying waistband/abdomen bumps.
    profiles=[(.70,.235,.182,-.027),(.76,.235,.182,-.027),(.92,.241,.182,-.027),(1.12,.248,.182,-.027),
              (1.28,.262,.170,-.015),(1.35,.260,.133,-.005),(1.405,.108,.085,0),(1.48,.083,.068,0)]
    rings=[np.column_stack((circle*np.array([rx,ry])+[0,cy],np.full(len(theta),z))) for z,rx,ry,cy in profiles]
    torso=loft('TorsoSolid',rings);parts=[torso];cuff_planes=[]
    for side,label in ((-1,'R'),(1,'L')):
        start=np.array([side*.215,-.006,1.335]);end=np.array(anchors['fit_wrist_'+label].translation)
        end[0]+=side*.016;axis=end-start;axis/=np.linalg.norm(axis)
        u=np.cross(axis,[0,1,0]);u/=np.linalg.norm(u);w=np.cross(axis,u)
        direction=np.cos(theta)[:,None]*u+np.sin(theta)[:,None]*w
        sleeve=[start-np.array([side*.075,0,.020])+direction*.055]
        for t,r in ((0,.065),(.18,.073),(.40,.067),(.65,.056),(.85,.049),(1.10,.043)):
            center=start+t*(end-start);sleeve.append(center+direction*r)
        parts.append(loft('SleeveSolid_'+label,sleeve));cuff_planes.append((end,axis))
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:obj.select_set(True)
    bpy.context.view_layer.objects.active=torso;bpy.ops.object.join();shirt=torso
    shirt.data.remesh_voxel_size=.006;shirt.data.remesh_voxel_adaptivity=0
    bpy.ops.object.voxel_remesh()
    smooth=shirt.modifiers.new('SmoothShoulderUnion','SMOOTH');smooth.factor=.75;smooth.iterations=12
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    decimate=shirt.modifiers.new('WorkingSurfaceDensity','DECIMATE');decimate.ratio=.5
    bpy.ops.object.modifier_apply(modifier=decimate.name)
    bm=bmesh.new();bm.from_mesh(shirt.data)
    for point,normal in [((0,0,.755),(0,0,-1)),((0,0,1.425),(0,0,1))]+cuff_planes:
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=point,plane_no=normal,
            dist=1e-6,clear_outer=True,clear_inner=False)
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(shirt.data);bm.free();shirt.data.update()
    v,f=geometry(shirt)
    before=inspect(v,f,body,body_faces)
    v,iterations=clear_body(v,f,body,body_faces,margin=.004,minimum_clearance=.0012,max_iterations=6)
    shirt.data.vertices.foreach_set('co',v.ravel());shirt.data.update()
    check=inspect(v,f,body,body_faces);require_clear(check)
    components=connected_components(f,len(v));loops=boundary_loops(f)
    if len(components)!=1 or len(loops)!=4:raise ValueError(f'Expected connected shirt with 4 openings: components={len(components)} openings={len(loops)}')
    pairs=tree(v,f).overlap(tree(pants_world,pants_faces))
    if pairs:
        q=v[f[np.unique(np.array(pairs)[:,0])]].reshape(-1,3)
        print('PAIR_BOUNDS',q.min(0),q.max(0),flush=True)
        raise ValueError('Shirt still crosses pants: '+str(len(pairs)))
    # A new uniform matte material avoids baked highlights from the damaged mesh.
    mat=bpy.data.materials.new('MatteBlackCotton');mat.use_nodes=True;mat.diffuse_color=(.018,.020,.023,1)
    bsdf=mat.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=mat.diffuse_color
    bsdf.inputs['Roughness'].default_value=.95;bsdf.inputs['Metallic'].default_value=0
    shirt.data.materials.clear();shirt.data.materials.append(mat)
    uv=shirt.data.uv_layers.new(name='GarmentUV')
    for poly in shirt.data.polygons:
        poly.use_smooth=True
        for index in poly.loop_indices:
            x,y,z=v[shirt.data.loops[index].vertex_index];uv.data[index].uv=((np.arctan2(y+.027,x)+np.pi)/(2*np.pi),z/1.5)
    placement=anchors['fit_anchor'];inverse=placement.inverted()
    local=np.array([inverse@Vector(p) for p in v]);shirt.data.vertices.foreach_set('co',local.ravel());shirt.data.update()
    spec={'body_length':67.,'garment_shoulder_width':52.,'chest_width':55.,'sleeve_length':47.}
    models=out/'models';models.mkdir(exist_ok=True)
    for name,kind,obj,current_spec,basis,old_entry in [('tripo_longsleeve_v12','crewneck',shirt,spec,'shoulder',None),
        (pants_name,'slacks',pants,entry['base_spec'],entry['sleeve_basis'],entry)]:
        hidden=[(o,list(o.users_collection)) for o in bpy.context.scene.objects if o!=obj]
        for o,collections in hidden:
            o.name='HiddenReference_'+o.name
            for collection in collections:collection.objects.unlink(o)
        register(obj,kind,current_spec,basis,name,models,30.)
        path=models/'registry.json';r=json.loads(path.read_text());e=r['templates'][name]
        if kind=='crewneck':
            points={'fit_anchor':np.zeros(3)}
            for label in ('L','R'):
                for old_tag,new_tag in (('shoulder','shoulder'),('wrist','cuff')):
                    points['fit_'+new_tag+'_'+label]=np.array(inverse@anchors['fit_'+old_tag+'_'+label].translation)
            e.update(revision='12',anchor_bindings=save_anchor_bindings(e,points))
        else:e.update(revision=old_entry['revision'],anchor_bindings=old_entry.get('anchor_bindings',{}))
        path.write_text(json.dumps(r,indent=2)+'\n')
        for o,collections in hidden:
            for collection in collections:collection.objects.link(o)
    shirt.matrix_world=placement;pants.matrix_world=anchors['fit_anchor_waist'];shirt.name='SmoothShirt';pants.name='PreservedPants';body_obj.name='ReferenceBody'
    bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(out/'reference-fitting.blend'),compress=True)
    report={'connected_components':len(components),'openings':len(loops),'body_before':before,'body_after':check,
        'shirt_pants_intersections':0,'iterations':iterations,'hem_width_cm':47.,'shoulder_design_width_cm':52.,
        'hem_to_shoulder_ratio':47/52,'pants_geometry_unchanged':True,'retopology':True,'material':'matte black'}
    (out/'repair-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS '+json.dumps({k:report[k] for k in ('connected_components','openings','shirt_pants_intersections','iterations')}),flush=True)


if __name__=='__main__':main()
