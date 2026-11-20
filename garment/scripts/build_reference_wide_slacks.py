# 역할: 벨트·고리를 제거하고 참고 이미지의 회색 와이드 팬츠를 기준 착장에 적용합니다.
import argparse
import json
from pathlib import Path
import shutil
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from geometry.template_binding import geometry
from prepare_template import register
from rebuild_cc0_reference import vertices_world,triangles,tree,inspect,boundary_loops,clear_body,save_anchor_bindings
from repair_reference_outfit import contours
from build_reference_tshirt import ordered_boundary


def remove_belt_loops(obj):
    bm=bmesh.new();bm.from_mesh(obj.data)
    remaining=set(bm.verts);groups=[]
    while remaining:
        seed=remaining.pop();group={seed};stack=[seed]
        while stack:
            vertex=stack.pop()
            for edge in vertex.link_edges:
                other=edge.other_vert(vertex)
                if other in remaining:remaining.remove(other);group.add(other);stack.append(other)
        groups.append(group)
    largest=max(groups,key=len)
    remove=[group for group in groups if group is not largest and
            max(vertex.co.z for vertex in group)>-.08 and len(group)<500]
    count=len(remove)
    if remove:bmesh.ops.delete(bm,geom=[vertex for group in remove for vertex in group],context='VERTS')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    return count


def profile(vertices,faces,z,side):
    loops=contours(vertices,faces,z)
    selected=[loop for loop in loops if side*loop[:,0].mean()>0]
    if not selected:raise ValueError('Missing separated leg section')
    q=max(selected,key=len)
    center=(q.min(0)+q.max(0))/2
    radius=(q.max(0)-q.min(0))/2
    return np.r_[center[:2],radius[:2]]


def reshape(obj,body_vertices,body_faces):
    original,faces=geometry(obj);result=original.copy()
    loops=boundary_loops(faces)
    waist=max(loops,key=lambda ids:original[ids,2].mean())
    hems=sorted([ids for ids in loops if original[ids,2].mean()<-.70],key=lambda ids:original[ids,0].mean())
    if len(hems)!=2:raise ValueError('Expected two open trouser hems')
    old_hem=float(np.mean([original[ids,2].mean() for ids in hems]))
    target_hem=float(body_vertices[:,2].min()+.05)
    for ids in hems:result[ids,2]=target_hem
    lower=original[:,2]<-.28
    result[lower,2]=-.28+(original[lower,2]+.28)*(target_hem+.28)/(old_hem+.28)
    for ids in hems:result[ids,2]=target_hem
    for side in (-1,1):
        levels=np.linspace(float(max(original[ids,2].max() for ids in hems)+.008),-.30,100)
        profiles=np.array([profile(original,faces,z,side) for z in levels])
        body_levels=np.linspace(-.87,-.34,60)
        body_profiles=np.array([profile(body_vertices,body_faces,z,side) for z in body_levels])
        ids=np.flatnonzero((side*original[:,0]>=0)&lower)
        old_z=original[ids,2];new_z=result[ids,2]
        source=np.column_stack([np.interp(old_z,levels,profiles[:,index]) for index in range(4)])
        target=np.column_stack([np.interp(np.clip(new_z,-.87,-.34),body_levels,body_profiles[:,index]) for index in range(4)])
        target[:,0]+=side*.008
        progress=np.clip((-.30-new_z)/(-.30-target_hem),0,1)
        rx=np.minimum(.111-.010*progress,np.abs(target[:,0])-.005)
        ry=.116-.003*progress
        normalized=(original[ids,:2]-source[:,:2])/np.maximum(source[:,2:],.001)
        mapped=target[:,:2]+normalized*np.column_stack((rx,ry))
        blend=np.clip((-.28-old_z)/.10,0,1);blend=blend*blend*(3-2*blend)
        result[ids,:2]=(1-blend[:,None])*original[ids,:2]+blend[:,None]*mapped
        # Restrained front and back press creases follow the new leg axes.
        front=np.clip((-normalized[:,1]-.25)/.6,0,1)
        crease=np.exp(-((result[ids,0]-target[:,0])/.012)**2)*blend
        result[ids,1]-=.0025*crease*front
        result[ids,1]+=.0012*crease*np.clip((normalized[:,1]-.3)/.6,0,1)
    # Level the waistband in its own body-waist coordinate frame.
    waist_delta=-float(original[waist,2].mean())
    weight=np.clip((original[:,2]+.08)/.07,0,1)
    result[:,2]+=weight*waist_delta
    result[waist,2]=0.
    front=np.clip((-result[:,1]-.03)/.07,0,1)
    pleat=np.exp(-((np.abs(result[:,0])-.078)/.010)**2)
    fade=np.clip((-result[:,2]-.015)/.045,0,1)*np.clip((result[:,2]+.34)/.20,0,1)
    result[:,1]-=.0025*front*pleat*fade
    obj.data.vertices.foreach_set('co',result.ravel());obj.data.update()
    return {'old_hem_z_m':old_hem,'target_hem_z_m':target_hem,'floor_clearance_target_cm':5.}


def rebuild_plain_band(obj):
    bm=bmesh.new();bm.from_mesh(obj.data)
    cut=-.035
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
        plane_co=(0,0,cut),plane_no=(0,0,1),dist=1e-7)
    remove=[face for face in bm.faces if face.calc_center_median().z>cut+1e-7]
    bmesh.ops.delete(bm,geom=remove,context='FACES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    edges=[edge for edge in bm.edges if edge.is_boundary and all(abs(v.co.z-cut)<1e-5 for v in edge.verts)]
    previous=ordered_boundary(edges)
    points=np.array([v.co[:] for v in previous])
    theta=np.arctan2(points[:,1]/.111,points[:,0]/.174)
    for amount in (.20,.45,.70,1.):
        target=np.column_stack((.174*np.cos(theta),.111*np.sin(theta),np.full(len(theta),cut*(1-amount))))
        target[:,:2]=points[:,:2]*(1-amount)+target[:,:2]*amount
        current=[bm.verts.new(point) for point in target]
        for index in range(len(previous)):
            nxt=(index+1)%len(previous)
            bm.faces.new((previous[index],current[index],current[nxt],previous[nxt]))
        previous=current
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    for face in bm.faces:face.smooth=True
    bm.to_mesh(obj.data);bm.free();obj.data.update()


def rebuild_straight_legs(obj,body_vertices,body_faces,hem):
    bm=bmesh.new();bm.from_mesh(obj.data)
    cut=-.31
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
        plane_co=(0,0,cut),plane_no=(0,0,1),dist=1e-7)
    remove=[face for face in bm.faces if face.calc_center_median().z<cut-1e-7]
    bmesh.ops.delete(bm,geom=remove,context='FACES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    remaining={edge for edge in bm.edges if edge.is_boundary and all(abs(v.co.z-cut)<1e-5 for v in edge.verts)}
    groups=[]
    while remaining:
        seed=remaining.pop();group={seed};stack=[seed]
        while stack:
            edge=stack.pop()
            for vertex in edge.verts:
                for other in vertex.link_edges:
                    if other in remaining:remaining.remove(other);group.add(other);stack.append(other)
        groups.append(group)
    if len(groups)!=2:raise ValueError('Expected two separate leg joins')
    for side in (-1,1):
        edges=next(group for group in groups if side*np.mean([v.co.x for edge in group for v in edge.verts])>0)
        previous=ordered_boundary(edges)
        join=np.array([v.co[:] for v in previous]);center=(join.min(0)+join.max(0))/2
        theta=np.arctan2((join[:,1]-center[1])/.11,(join[:,0]-center[0])/.11)
        ankle=profile(body_vertices,body_faces,-.87,side)
        endpoint=np.array([ankle[0]+side*.008,ankle[1]])
        for amount in np.linspace(0,1,61)[1:]:
            z=cut+(hem-cut)*amount
            axis=center[:2]*(1-amount)+endpoint*amount
            rx=min(.106,abs(axis[0])-.005);ry=.120
            target=np.column_stack((axis[0]+rx*np.cos(theta),axis[1]+ry*np.sin(theta),np.full(len(theta),z)))
            crease=np.exp(-((np.cos(theta))/.14)**2)
            target[:,1]-=.0035*crease*np.clip(-np.sin(theta),0,1)
            target[:,1]+=.0012*crease*np.clip(np.sin(theta),0,1)
            blend=min(1.,amount/.18);blend=blend*blend*(3-2*blend)
            initial=join.copy();initial[:,2]=z
            target=initial*(1-blend)+target*blend
            current=[bm.verts.new(point) for point in target]
            for index in range(len(previous)):
                nxt=(index+1)%len(previous)
                bm.faces.new((previous[index],current[index],current[nxt],previous[nxt]))
            previous=current
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    for face in bm.faces:face.smooth=True
    bm.to_mesh(obj.data);bm.free();obj.data.update()


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
    body=next(obj for obj in bpy.context.scene.objects if obj.type=='MESH')
    world_body=vertices_world(body);body_faces=triangles(body)
    anchor_world={obj.name:obj.matrix_world.copy() for obj in bpy.context.scene.objects if obj.name.startswith('fit_')}
    loaded={}
    for name,entry in source['templates'].items():
        with bpy.data.libraries.load(str((args.models/entry['blend']).resolve()),link=False) as (src,dst):dst.objects=[entry['object']]
        obj=dst.objects[0];bpy.context.collection.objects.link(obj);loaded[entry['kind']]=(name,entry,obj)
    _,entry,pants_obj=loaded['slacks'];shirt_name,shirt_entry,shirt_obj=loaded['crewneck']
    placement=anchor_world['fit_anchor_waist'];inverse=placement.inverted()
    local_body=np.array([inverse @ Vector(point) for point in world_body])
    removed=remove_belt_loops(pants_obj)
    shaping=reshape(pants_obj,local_body,body_faces)
    rebuild_plain_band(pants_obj)
    rebuild_straight_legs(pants_obj,local_body,body_faces,shaping['target_hem_z_m'])
    pants,faces=geometry(pants_obj)
    pants,iterations=clear_body(pants,faces,local_body,body_faces,margin=.003,minimum_clearance=.0012)
    pants_obj.data.vertices.foreach_set('co',pants.ravel());pants_obj.data.update()
    material=bpy.data.materials.new('Medium grey woven slacks');material.use_nodes=True
    material.diffuse_color=(.42,.43,.42,1)
    shader=material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=material.diffuse_color
    shader.inputs['Roughness'].default_value=.9
    shader.inputs['Specular IOR Level'].default_value=.20
    pants_obj.data.materials.clear();pants_obj.data.materials.append(material)
    for face in pants_obj.data.polygons:face.material_index=0;face.use_smooth=True
    check=inspect(pants,faces,local_body,body_faces)
    shirt,shirt_faces=geometry(shirt_obj)
    transform=inverse @ anchor_world['fit_anchor']
    shirt_local=np.array([transform @ Vector(point) for point in shirt])
    pair=len(tree(pants,faces).overlap(tree(shirt_local,shirt_faces)))
    if pair or check['body_triangle_intersections'] or any(check[k]['inside'] for k in ('vertices','edge_midpoints','triangle_centroids')):
        raise ValueError('Body or shirt intersection remains: '+str(pair))
    loops=boundary_loops(faces)
    if len(loops)!=3 or check['topology']['nonmanifold_edges_gt2'] or check['topology']['degenerate_triangles']:
        raise ValueError('Invalid trouser topology')
    anchors={name:np.array(binding['reference']) for name,binding in entry['anchor_bindings'].items()}
    for side,label in [(-1,'R'),(1,'L')]:
        hem=next(ids for ids in loops if pants[ids,2].mean()<-.7 and side*pants[ids,0].mean()>0)
        anchors['fit_hem_'+label]=pants[hem].mean(0)
    name='grey_wide_slacks_cc0_v5';models=output/'models';models.mkdir(exist_ok=True)
    spec=dict(entry['base_spec'],knee_width=26.,hem_width=25.)
    for item in list(bpy.context.scene.objects):
        if item!=pants_obj:bpy.data.objects.remove(item,do_unlink=True)
    register(pants_obj,'slacks',spec,'none',name,models,25.)
    registry=json.loads((models/'registry.json').read_text())
    registry['templates'][name].update(revision='5',anchor_bindings=save_anchor_bindings(registry['templates'][name],anchors),
        saved_with_blender=bpy.app.version_string,reference_body_sha256=entry['reference_body_sha256'])
    for key in ('blend','binding'):shutil.copyfile(args.models/shirt_entry[key],models/shirt_entry[key])
    registry['templates'][shirt_name]=shirt_entry
    (models/'registry.json').write_text(json.dumps(registry,indent=2)+'\n')
    report={'style_reference':'User supplied grey wide slacks images; no belt or belt loops',
        'template_id':name,'blender_version':bpy.app.version_string,'removed_belt_loop_components':removed,
        'shaping':shaping,'spec':spec,'body_collision':check,'shirt_pants_triangle_intersections':pair,
        'intentional_openings':len(loops),'clearance_iterations':iterations}
    (output/'slacks-report.json').write_text(json.dumps(report,indent=2)+'\n')
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    def mesh(name,v,f,color):
        data=bpy.data.meshes.new(name);data.from_pydata(v.tolist(),[],f.tolist());data.update()
        obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
        mat=bpy.data.materials.new(name);mat.diffuse_color=(*color,1);obj.data.materials.append(mat)
        for face in obj.data.polygons:face.use_smooth=True
    mesh('ReferenceBody',world_body,body_faces,(.55,.61,.67))
    mesh('WhiteTshirt',np.array([anchor_world['fit_anchor'] @ Vector(point) for point in shirt]),shirt_faces,(.80,.81,.79))
    mesh('Slacks',np.array([placement @ Vector(point) for point in pants]),faces,(.42,.43,.42))
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'reference-fitting.blend'),compress=True)
    print('PASS: grey wide slacks, removed belt loops='+str(removed)+', body/shirt intersections=0',flush=True)


if __name__=='__main__':main()
