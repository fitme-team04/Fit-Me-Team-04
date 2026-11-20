# 역할: 손상된 Tripo 상의의 연결 메시와 무광 재질을 재구성해 밑단·소매가 자연스러운 기준 착장을 만듭니다.
import argparse,json,sys
from pathlib import Path
import bpy,bmesh
import numpy as np
from scipy.spatial import ConvexHull
from scipy import sparse
from scipy.sparse.linalg import spsolve
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from geometry.garment_cages import cage
from geometry.template_binding import geometry
from geometry.body_clearance import require_clear
from prepare_template import register
from rebuild_cc0_reference import tree,inspect,clear_body,save_anchor_bindings,vertices_world,triangles,boundary_loops
from repair_reference_outfit import enclosing_ring


def main():
    p=argparse.ArgumentParser()
    for name in ('models','body','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    registry=json.loads((args.models/'registry.json').read_text())
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(args.body.resolve()))
    body_obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    body_world=vertices_world(body_obj);body_faces=triangles(body_obj)
    anchors={o.name:o.matrix_world.copy() for o in bpy.context.scene.objects if o.name.startswith('fit_')}
    placement=anchors['fit_anchor'];inverse=placement.inverted()
    body=np.array([inverse@Vector(v) for v in body_world])
    loaded={}
    for name,entry in registry['templates'].items():
        with bpy.data.libraries.load(str((args.models/entry['blend']).resolve()),link=False) as (src,dst):dst.objects=[entry['object']]
        obj=dst.objects[0];bpy.context.collection.objects.link(obj);loaded[entry['kind']]=(name,entry,obj)
    _,old_entry,old=loaded['crewneck'];pants_name,pants_entry,pants=loaded['slacks']
    source,source_faces=geometry(old);old.data.calc_loop_triangles()
    uv_layer=old.data.uv_layers.active
    source_uv=np.array([[uv_layer.data[i].uv[:] for i in t.loops] for t in old.data.loop_triangles])
    source_tree=tree(source,source_faces)
    pants_local=np.array([inverse@anchors['fit_anchor_waist']@Vector(v) for v in geometry(pants)[0]])
    pants_faces=geometry(pants)[1]
    spec={'body_length':68.,'garment_shoulder_width':44.,'chest_width':55.,'sleeve_length':47.}
    v,f,_,_=cage('crewneck',spec,'shoulder')
    mesh=bpy.data.meshes.new('RebuiltShirt');mesh.from_pydata(v.tolist(),[],f.tolist());mesh.update()
    shirt=bpy.data.objects.new('RebuiltShirt',mesh);bpy.context.collection.objects.link(shirt)
    for mat in old.data.materials:mesh.materials.append(mat.copy())
    bpy.context.view_layer.objects.active=shirt
    sub=shirt.modifiers.new('SmoothConnectedSurface','SUBSURF');sub.levels=2
    bpy.ops.object.modifier_apply(modifier=sub.name)
    v,f=geometry(shirt)
    # A relaxed torso covers the waistband without tracking its bumps.
    profiles={};angles=np.linspace(-np.pi,np.pi,128,endpoint=False)
    for index,point in enumerate(v):
        x,y,z=point
        if z<0 and abs(x)<.30:
            theta=float(np.arctan2(y+.025,x));level=round(float(z),2)
            if level not in profiles:
                # Open scan seams need not form a closed section: use a vertex slab envelope.
                center=np.array([0.,-.025]);direction=np.column_stack((np.cos(angles),np.sin(angles)))
                garment_points=pants_local[np.abs(pants_local[:,2]-level)<.025,:2]
                body_points=body[(np.abs(body[:,2]-level)<.015)&(np.abs(body[:,0])<.215),:2]
                style=center+direction*np.array([.225,.15])
                hull=ConvexHull(np.vstack((garment_points,body_points,style)))
                normal=hull.equations[:,:2];offset=hull.equations[:,2]-.018
                denominator=normal@direction.T;numerator=-(normal@center+offset)
                radius=np.min(np.divide(numerator[:,None],denominator,out=np.full_like(denominator,np.inf),where=denominator>1e-10),axis=0)
                profiles[level]=np.column_stack((center+direction*radius[:,None],np.full(len(angles),level)))
            ring=profiles[level];target=np.array([np.interp(theta,np.r_[angles,np.pi],np.r_[ring[:,k],ring[0,k]]) for k in (0,1)])
            weight=np.clip(-z/.10,0,1);weight=.97*weight*weight*(3-2*weight)
            side_weight=np.clip((.30-abs(x))/.055,0,1)
            weight*=side_weight*side_weight*(3-2*side_weight)
            v[index,:2]=(1-weight)*point[:2]+weight*target
    # Smooth tapered cuffs, using the actual shoulder/wrist axes.
    for side,label in ((-1,'R'),(1,'L')):
        shoulder=np.array(inverse@anchors['fit_shoulder_'+label].translation)
        wrist=np.array(inverse@anchors['fit_wrist_'+label].translation)
        axis=wrist-shoulder;length=np.linalg.norm(axis);axis/=length
        q=v-shoulder;t=q@axis;radial=q-t[:,None]*axis
        distance=np.linalg.norm(radial,axis=1)
        mask=(side*v[:,0]>.26)&(t>.10)&(distance<.19)
        progress=np.clip(t/length,0,1)
        desired=.072*(1-progress)+.043*progress
        weight=np.clip((t-.10)/.14,0,1);weight=.94*weight*weight*(3-2*weight)
        radius=(1-weight)*distance+weight*desired
        v[mask]=shoulder+t[mask,None]*axis+radial[mask]/np.maximum(distance[mask,None],1e-8)*radius[mask,None]
    # Replace the deep, uneven generated neckline with a shallow crew neck.
    loops=boundary_loops(f)
    neck=max(loops,key=lambda ids:v[ids,2].mean())
    center=v[neck,:2].mean(0);theta=np.arctan2(v[neck,1]-center[1],v[neck,0]-center[0])
    target=np.column_stack((.082*np.cos(theta),.068*np.sin(theta),.045+.012*np.sin(theta)))
    edges=np.unique(np.sort(np.vstack((f[:,[0,1]],f[:,[1,2]],f[:,[2,0]])),axis=1),axis=0)
    a,b=edges.T;links=sparse.coo_matrix((np.ones(2*len(a)),(np.r_[a,b],np.r_[b,a])),shape=(len(v),len(v))).tocsr()
    lap=sparse.diags(np.asarray(links.sum(1)).ravel())-links
    fixed=(v[:,2]<-.14)|(np.abs(v[:,0])>.215);fixed[neck]=True
    displacement=np.zeros_like(v);displacement[neck]=target-v[neck]
    free=np.flatnonzero(~fixed);bound=np.flatnonzero(fixed)
    displacement[free]=spsolve((lap[free][:,free]+.015*sparse.eye(len(free))).tocsc(),-lap[free][:,bound]@displacement[bound])
    v+=displacement
    shirt.data.vertices.foreach_set('co',v.ravel());shirt.data.update()
    bm=bmesh.new();bm.from_mesh(shirt.data)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(shirt.data);bm.free();shirt.data.update()
    v,f=geometry(shirt)
    v,iterations=clear_body(v,f,body,body_faces,margin=.004,minimum_clearance=.0012,max_iterations=12)
    shirt.data.vertices.foreach_set('co',v.ravel());shirt.data.update()
    area=np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)/2
    if (area<1e-12).any():
        bm=bmesh.new();bm.from_mesh(shirt.data);bm.verts.ensure_lookup_table()
        candidates=np.unique(f[area<1e-12])
        bmesh.ops.remove_doubles(bm,verts=[bm.verts[int(i)] for i in candidates],dist=1e-6)
        bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-8)
        bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(shirt.data);bm.free();shirt.data.update()
        v,f=geometry(shirt)
        v,extra=clear_body(v,f,body,body_faces,margin=.004,minimum_clearance=.0012,max_iterations=4)
        iterations+=extra;shirt.data.vertices.foreach_set('co',v.ravel());shirt.data.update()
    # Separate near-collinear points by 0.05mm without deleting cloth faces.
    for _ in range(3):
        area=np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)/2
        bad=f[area<1e-12]
        if not len(bad):break
        for ids in bad:
            pairs=[(0,1,2),(1,2,0),(2,0,1)]
            a,b,c=max(pairs,key=lambda q:np.linalg.norm(v[ids[q[1]]]-v[ids[q[0]]]))
            edge=v[ids[b]]-v[ids[a]];normal=np.cross(edge,[0,0,1])
            if np.linalg.norm(normal)<1e-10:normal=np.cross(edge,[1,0,0])
            v[ids[c]]+=normal/np.linalg.norm(normal)*.00005
    shirt.data.vertices.foreach_set('co',v.ravel());shirt.data.update()
    print('FITME_REPAIR_CHECK '+json.dumps(inspect(v,f,body,body_faces)),flush=True)
    check=inspect(v,f,body,body_faces);require_clear(check)
    pair=len(tree(v,f).overlap(tree(pants_local,pants_faces)))
    if pair:
        pairs=tree(v,f).overlap(tree(pants_local,pants_faces))
        bad=v[f[np.unique(np.array(pairs)[:,0])]].reshape(-1,3)
        print('FITME_PAIR_BOUNDS '+json.dumps({'min':bad.min(0).tolist(),'max':bad.max(0).tolist()}),flush=True)
        raise ValueError('Rebuilt shirt still crosses pants: '+str(pair))
    # Transfer the Tripo material UVs to the new connected surface.
    uv=shirt.data.uv_layers.new(name='TripoTransferredUV')
    for poly in shirt.data.polygons:
        for loop in poly.loop_indices:
            point=v[shirt.data.loops[loop].vertex_index]
            nearest,_,face,_=source_tree.find_nearest(Vector(point))
            a,b,c=source[source_faces[face]]
            w=np.linalg.lstsq(np.column_stack((b-a,c-a)),np.asarray(nearest)-a,rcond=None)[0]
            uv.data[loop].uv=np.array([1-w.sum(),w[0],w[1]])@source_uv[face]
        poly.use_smooth=True
    for mat in shirt.data.materials:
        mat.diffuse_color=(.018,.020,.023,1.)
        if mat.use_nodes:
            for node in list(mat.node_tree.nodes):
                if node.type=='TEX_IMAGE':mat.node_tree.nodes.remove(node)
            for node in mat.node_tree.nodes:
                if node.type=='BSDF_PRINCIPLED':
                    for socket in ('Base Color','Normal'):
                        for link in list(node.inputs[socket].links):mat.node_tree.links.remove(link)
                    node.inputs['Base Color'].default_value=(.018,.020,.023,1.)
                    node.inputs['Roughness'].default_value=.94;node.inputs['Metallic'].default_value=0
    bpy.data.objects.remove(old,do_unlink=True)
    models=out/'models';models.mkdir(exist_ok=True)
    # Store each template independently, retaining the original pants and anchors.
    for name,kind,obj,entry,current_spec in [('tripo_longsleeve_v11','crewneck',shirt,old_entry,spec),(pants_name,'slacks',pants,pants_entry,pants_entry['base_spec'])]:
        hidden=[(o,list(o.users_collection)) for o in bpy.context.scene.objects if o!=obj]
        for o,collections in hidden:
            o.name='HiddenReference_'+o.name
            for collection in collections:collection.objects.unlink(o)
        register(obj,kind,current_spec,entry['sleeve_basis'],name,models,30.)
        path=models/'registry.json';r=json.loads(path.read_text());r['templates'][name]['revision']='11' if kind=='crewneck' else entry['revision']
        if kind=='crewneck':
            points={'fit_anchor':np.zeros(3)}
            for label in ('L','R'):
                for source_tag,target_tag in (('shoulder','shoulder'),('wrist','cuff')):
                    points['fit_'+target_tag+'_'+label]=np.array(inverse@anchors['fit_'+source_tag+'_'+label].translation)
            r['templates'][name]['anchor_bindings']=save_anchor_bindings(r['templates'][name],points)
        else:r['templates'][name]['anchor_bindings']=entry.get('anchor_bindings',{})
        path.write_text(json.dumps(r,indent=2)+'\n')
        for o,collections in hidden:
            for collection in collections:collection.objects.link(o)
    shirt.matrix_world=placement;pants.matrix_world=anchors['fit_anchor_waist']
    shirt.name='RebuiltShirt';pants.name='PreservedPants';body_obj.name='ReferenceBody'
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'reference-fitting.blend'),compress=True)
    report={'retopology':True,'tripo_uv_transfer_for_reference':True,'material':'uniform matte black; baked-lighting texture removed','pants_geometry_unchanged':True,'spec':spec,'body':check,
        'shirt_pants_triangle_intersections':pair,'iterations':iterations,'scope':'baseline body only; previous v10 matrix not reused'}
    (out/'repair-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: rebuilt shirt baseline, body and pants intersections=0',flush=True)


if __name__=='__main__':main()
