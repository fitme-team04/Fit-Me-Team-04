# 역할: 상의 몸통 옆면과 밑단을 재구성하고 신체·바지와 겹치지 않는 기준 착장을 만듭니다.
import argparse
import json
from pathlib import Path
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from scipy.spatial import ConvexHull

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from geometry.template_binding import geometry
from prepare_template import register
from rebuild_cc0_reference import vertices_world,triangles,tree,inspect,boundary_loops,clear_body


def contours(vertices,faces,z):
    distance=vertices[:,2]-z
    signs=distance[faces]>0
    cuts=faces[signs.any(1)&~signs.all(1)]
    graph={}
    for tri in cuts:
        ends=[]
        for a,b in zip(tri,np.roll(tri,1)):
            if (distance[a]>0)!=(distance[b]>0):ends.append(tuple(sorted((a,b))))
        a,b=ends;graph.setdefault(a,[]).append(b);graph.setdefault(b,[]).append(a)
    result=[]
    while graph:
        start=next(iter(graph));current=start;previous=None;loop=[]
        while current in graph:
            loop.append(current);neighbors=graph.pop(current)
            nxt=next((n for n in neighbors if n!=previous),None)
            previous,current=current,nxt
        if current==start and len(loop)>3:
            a,b=np.asarray(loop).T
            alpha=distance[a]/(distance[a]-distance[b])
            result.append(vertices[a]*(1-alpha[:,None])+vertices[b]*alpha[:,None])
    return result


def enclosing_ring(z,theta,body,pants,margin=.008,style=(.215,.135),torso_only=False):
    loops=contours(*body,z)
    central=[loop for loop in loops if loop[:,0].min()<0<loop[:,0].max()]
    body_points=np.vstack(central or loops)[:,:2]
    if torso_only and z>-.33:
        body_points=body_points[np.abs(body_points[:,0])<.215]
    pant_loops=contours(*pants,z)
    points=[body_points]
    if pant_loops:points.append(np.vstack(pant_loops)[:,:2])
    center=np.array([0.,-.025])
    angles=np.linspace(-np.pi,np.pi,96,endpoint=False)
    points.append(center+np.column_stack((np.cos(angles)*style[0],np.sin(angles)*style[1])))
    hull=ConvexHull(np.vstack(points))
    normals=hull.equations[:,:2];offset=hull.equations[:,2]-margin
    # Midpoint of bounds is inside this convex torso envelope.
    xy=np.vstack(points);center=(xy.min(0)+xy.max(0))/2
    direction=np.column_stack((np.cos(theta),np.sin(theta)))
    denominator=normals @ direction.T
    numerator=-(normals @ center+offset)
    radius=np.min(np.divide(numerator[:,None],denominator,
                  out=np.full_like(denominator,np.inf),where=denominator>1e-10),axis=0)
    return np.column_stack((center+direction*radius[:,None],np.full(len(theta),z)))


def rebuild_torso(obj,body,pants,length_cm,fitted=False,wrinkles=False):
    cut=-.16 if fitted else -.18
    original,_=geometry(obj)
    hem=float(original[:,2].max()-length_cm/100)
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
        plane_co=(0,0,cut),plane_no=(0,0,1),dist=1e-7)
    lower={face for face in bm.faces if face.calc_center_median().z<cut-1e-7}
    groups=[]
    while lower:
        seed=lower.pop();group={seed};stack=[seed]
        while stack:
            face=stack.pop()
            for edge in face.edges:
                for other in edge.link_faces:
                    if other in lower:lower.remove(other);group.add(other);stack.append(other)
        groups.append(group)
    torso=[]
    for group in groups:
        xs=[v.co.x for face in group for v in face.verts]
        if min(xs)<0<max(xs):torso.extend(group)
    if not torso:raise ValueError('Cannot isolate lower torso without sleeves')
    bmesh.ops.delete(bm,geom=torso,context='FACES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    border=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-cut)<1e-5 for v in e.verts)]
    adjacent={}
    for edge in border:
        a,b=edge.verts;adjacent.setdefault(a,[]).append(b);adjacent.setdefault(b,[]).append(a)
    if not adjacent or any(len(n)!=2 for n in adjacent.values()):raise ValueError('Torso join is not a closed ring')
    start=next(iter(adjacent));ordered=[start];previous=None;current=start
    while True:
        nxt=next(v for v in adjacent[current] if v!=previous)
        if nxt==start:break
        ordered.append(nxt);previous,current=current,nxt
    if len(ordered)!=len(adjacent):raise ValueError('Unexpected extra torso openings')
    join=np.array([v.co[:] for v in ordered]);center=join[:,:2].mean(0)
    theta=np.arctan2(join[:,1]-center[1],join[:,0]-center[0])
    amounts=np.linspace(0,1,41)[1:]
    profiles=[]
    for amount in amounts:
        z=cut+(hem-cut)*amount
        style=(float(np.interp(z,[hem,-.39,cut],[.20,.185,.205])),
               float(np.interp(z,[hem,-.39,cut],[.14,.115,.15]))) if fitted else (.215,.135)
        profiles.append(enclosing_ring(z,theta,body,pants,margin=.012 if fitted else .008,style=style,torso_only=fitted))
    # A straight relaxed torso avoids following each waistband/hip bulge.
    envelope=ConvexHull(np.vstack([profile[:,:2] for profile in profiles]))
    normals=envelope.equations[:,:2];offset=envelope.equations[:,2]
    direction=np.column_stack((np.cos(theta),np.sin(theta)))
    denominator=normals @ direction.T
    radius=np.min(np.divide(-(normals @ center+offset)[:,None],denominator,
        out=np.full_like(denominator,np.inf),where=denominator>1e-10),axis=0)
    outline=center+direction*radius[:,None]
    previous=ordered
    for row,amount in enumerate(amounts):
        z=cut+(hem-cut)*amount
        desired=profiles[row].copy() if fitted else np.column_stack((outline,np.full(len(theta),z)))
        if wrinkles:
            local=desired[:,:2]-desired[:,:2].mean(0)
            normals=local/np.linalg.norm(local,axis=1)[:,None]
            weight=np.exp(-((z-(hem+.085))/.10)**2)*(.45+.55*np.abs(np.sin(theta)))
            displacement=weight*(.0034*np.sin(65*z+4.3*np.sin(theta))+.0006*np.sin(137*z-5.1*theta))
            desired[:,:2]+=normals*displacement[:,None]
        influence=min(1.,amount/.22);influence=influence*influence*(3-2*influence)
        target=join.copy();target[:,2]=z
        target=(1-influence)*target+influence*desired
        current=[bm.verts.new(point) for point in target]
        for index in range(len(previous)):
            nxt=(index+1)%len(previous)
            bm.faces.new((previous[index],current[index],current[nxt],previous[nxt]))
        previous=current
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    for face in bm.faces:face.smooth=True
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    return {'torso_cut_z_m':cut,'hem_z_m':hem,'join_vertices':len(ordered),'torso_rings':41}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--models',required=True,type=Path)
    parser.add_argument('--body',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    source=json.loads((args.models/'registry.json').read_text())
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(args.body.resolve()))
    body_obj=next(obj for obj in bpy.context.scene.objects if obj.type=='MESH')
    body_vertices=vertices_world(body_obj);body_faces=triangles(body_obj)
    anchors={obj.name:obj.matrix_world.copy() for obj in bpy.context.scene.objects if obj.name.startswith('fit_')}
    loaded={}
    for name,entry in source['templates'].items():
        with bpy.data.libraries.load(str((args.models/entry['blend']).resolve()),link=False) as (src,dst):dst.objects=[entry['object']]
        obj=dst.objects[0];bpy.context.collection.objects.link(obj)
        loaded[entry['kind']]=(name,entry,obj)
    top_name,top_entry,top_obj=loaded['crewneck']
    pants_name,pants_entry,pants_obj=loaded['slacks']
    top_place=anchors['fit_anchor'];pants_place=anchors['fit_anchor_waist']
    to_top=top_place.inverted() @ pants_place
    pants_original,pants_faces=geometry(pants_obj)
    pants=pants_original.copy()
    influence=np.clip((pants[:,2]+.45)/.25,0,1)
    pants[:,:2]*=(1-.01*influence[:,None])
    local_body_pants=np.array([pants_place.inverted() @ Vector(p) for p in body_vertices])
    pants,_=clear_body(pants,pants_faces,local_body_pants,body_faces,margin=.0025)
    pants_obj.data.vertices.foreach_set('co',pants.ravel());pants_obj.data.update()
    pants_in_top=np.array([to_top @ Vector(p) for p in pants])
    body_in_top=np.array([top_place.inverted() @ Vector(p) for p in body_vertices])
    original_top,original_faces=geometry(top_obj)
    before_pairs=len(tree(original_top,original_faces).overlap(tree(pants_in_top,pants_faces)))
    rebuilt=rebuild_torso(top_obj,(body_in_top,body_faces),(pants_in_top,pants_faces),top_entry['base_spec']['body_length'])
    top,top_faces=geometry(top_obj)
    top,_=clear_body(top,top_faces,body_in_top,body_faces,margin=.0025)
    top_obj.data.vertices.foreach_set('co',top.ravel());top_obj.data.update()
    pair_count=len(tree(top,top_faces).overlap(tree(pants_in_top,pants_faces)))
    report={'body_reference':str(args.body),'saved_with_blender':bpy.app.version_string,
        'garment_intersections_before':before_pairs,'garment_intersections_after':pair_count,
        'torso_rebuild':rebuilt,'garments':{}}
    scenes=[]
    for kind,name,entry,obj,vertices,faces,placement,body in [
        ('crewneck',top_name,top_entry,top_obj,top,top_faces,top_place,body_in_top),
        ('slacks',pants_name,pants_entry,pants_obj,pants,pants_faces,pants_place,local_body_pants)]:
        check=inspect(vertices,faces,body,body_faces)
        loops=boundary_loops(faces)
        check['boundary_loops']=len(loops)
        check['boundary_z_ranges_m']=[[float(vertices[ids,2].min()),float(vertices[ids,2].max())] for ids in loops]
        if check['body_triangle_intersections'] or any(check[k]['inside'] for k in ('vertices','edge_midpoints','triangle_centroids')):
            raise ValueError('Body collision remains: '+name)
        if check['topology']['nonmanifold_edges_gt2'] or check['topology']['degenerate_triangles']:
            raise ValueError('Invalid outfit topology')
        if len(loops)!=(4 if kind=='crewneck' else 3):raise ValueError('Unexpected garment opening')
        new_name=name.replace('_v2','_v3')
        report['garments'][new_name]=check
        scenes.append((new_name,vertices.copy(),faces.copy(),placement.copy()))
    if pair_count:raise ValueError('Shirt/pants intersection remains: '+str(pair_count))
    models=output/'models';models.mkdir(exist_ok=True)
    # Store only the intended mesh per template.
    for kind,name,entry,obj in [('crewneck',top_name,top_entry,top_obj),('slacks',pants_name,pants_entry,pants_obj)]:
        other=[(item,list(item.users_collection)) for item in bpy.context.scene.objects if item!=obj]
        for item,collections in other:
            item.name='HiddenReference_'+item.name
            for collection in collections:collection.objects.unlink(item)
        new_name=name.replace('_v2','_v3')
        register(obj,kind,entry['base_spec'],entry['sleeve_basis'],new_name,models,25.)
        path=models/'registry.json';registry=json.loads(path.read_text())
        registry['templates'][new_name].update({k:entry[k] for k in ['anchor_bindings','reference_body_sha256']})
        registry['templates'][new_name].update(revision='3',saved_with_blender=bpy.app.version_string)
        path.write_text(json.dumps(registry,indent=2)+'\n')
        for item,collections in other:
            for collection in collections:collection.objects.link(item)
    (output/'outfit-report.json').write_text(json.dumps(report,indent=2)+'\n')
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    def mesh(name,v,f,color):
        data=bpy.data.meshes.new(name);data.from_pydata(v.tolist(),[],f.tolist());data.update()
        obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
        mat=bpy.data.materials.new(name);mat.diffuse_color=(*color,1);obj.data.materials.append(mat)
        for face in obj.data.polygons:face.use_smooth=True
    mesh('ReferenceBody',body_vertices,body_faces,(.65,.72,.78))
    for name,v,f,placement in scenes:mesh(name,np.array([placement @ Vector(p) for p in v]),f,(.025,.045,.065))
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'reference-fitting.blend'),compress=True)
    print('PASS: torso rebuilt; body and shirt/pants triangle intersections are zero',flush=True)


if __name__=='__main__':main()
