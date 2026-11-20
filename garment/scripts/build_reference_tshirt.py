# 역할: 참고 이미지의 흰색 크루넥 반팔·밑단 주름을 기준 착장 템플릿에 반영합니다.
import argparse
import json
from pathlib import Path
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
from repair_reference_outfit import rebuild_torso


def ordered_boundary(edges):
    adjacent={}
    for edge in edges:
        a,b=edge.verts;adjacent.setdefault(a,[]).append(b);adjacent.setdefault(b,[]).append(a)
    if not adjacent or any(len(v)!=2 for v in adjacent.values()):raise ValueError('Invalid opening')
    start=next(iter(adjacent));ordered=[start];current=start;previous=None
    while True:
        nxt=next(v for v in adjacent[current] if v!=previous)
        if nxt==start:break
        ordered.append(nxt);previous,current=current,nxt
    if len(ordered)!=len(adjacent):raise ValueError('Multiple unexpected openings')
    return ordered


def shorten_sleeves(obj,shoulders,wrists,run=.22):
    bm=bmesh.new();bm.from_mesh(obj.data)
    anchors={}
    for label,side in [('L',1),('R',-1)]:
        axis=wrists[label]-shoulders[label];axis/=np.linalg.norm(axis)
        center=shoulders[label]+axis*run
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
            plane_co=center,plane_no=axis,dist=1e-7)
        outside={face for face in bm.faces if (np.array(face.calc_center_median())-center) @ axis>1e-7}
        groups=[]
        while outside:
            seed=outside.pop();group={seed};stack=[seed]
            while stack:
                face=stack.pop()
                for edge in face.edges:
                    for other in edge.link_faces:
                        if other in outside:outside.remove(other);group.add(other);stack.append(other)
            groups.append(group)
        remove=[]
        for group in groups:
            xs=[side*v.co.x for face in group for v in face.verts]
            if min(xs)>.20 and max(xs)>.40:remove.extend(group)
        if not remove:raise ValueError('Cannot isolate distal sleeve')
        bmesh.ops.delete(bm,geom=remove,context='FACES')
        loose=[v for v in bm.verts if not v.link_faces]
        if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
        edges=[edge for edge in bm.edges if edge.is_boundary and all(
            abs((np.array(v.co)-center) @ axis)<1e-5 and side*v.co.x>.20 for v in edge.verts)]
        previous=ordered_boundary(edges)
        points=np.array([v.co[:] for v in previous]);radial=points-points.mean(0)
        up=np.array([0.,0.,1.]);up-=axis*(up @ axis);up/=np.linalg.norm(up)
        across=np.cross(axis,up)
        ru=float(np.ptp(radial @ up)/2);rv=float(np.ptp(radial @ across)/2)
        angles=np.arctan2((radial @ across)/rv,(radial @ up)/ru)
        radial=np.cos(angles)[:,None]*up*ru+np.sin(angles)[:,None]*across*rv
        for vertex,point in zip(previous,center+radial):vertex.co=point
        for shift,scale in [(.003,1.),(.003,.97),(-.004,.97)]:
            current=[bm.verts.new(point) for point in center+radial*scale+axis*shift]
            for index in range(len(previous)):
                nxt=(index+1)%len(previous)
                bm.faces.new((previous[index],current[index],current[nxt],previous[nxt]))
            previous=current
        anchors['fit_cuff_'+label]=center
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    for face in bm.faces:face.smooth=True
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    return anchors


def collar_band(obj):
    bm=bmesh.new();bm.from_mesh(obj.data)
    edges=[edge for edge in bm.edges if edge.is_boundary and all(v.co.z>.005 and abs(v.co.x)<.13 for v in edge.verts)]
    region={face for edge in edges for face in edge.link_faces}
    for _ in range(5):
        neighbors={other for face in region for edge in face.edges for other in edge.link_faces
                   if other.calc_center_median().z>-.025 and abs(other.calc_center_median().x)<.14}
        region|=neighbors
    bmesh.ops.delete(bm,geom=list(region),context='FACES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    edges=[edge for edge in bm.edges if edge.is_boundary and all(v.co.z>-.04 and abs(v.co.x)<.155 for v in edge.verts)]
    previous=ordered_boundary(edges)
    points=np.array([v.co[:] for v in previous])
    angles=np.arctan2((points[:,1]+.006)/.07,points[:,0]/.10)
    inner=np.column_stack((.078*np.cos(angles),-.006+.057*np.sin(angles),.045+.012*np.sin(angles)))
    for amount in (.25,.50,.75,1.):
        target=points*(1-amount)+inner*amount
        target[:,2]+=.002*np.sin(np.pi*amount)
        current=[bm.verts.new(point) for point in target]
        for index in range(len(previous)):
            nxt=(index+1)%len(previous)
            bm.faces.new((previous[index],current[index],current[nxt],previous[nxt]))
        previous=current
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    for face in bm.faces:face.smooth=True
    bm.to_mesh(obj.data);bm.free();obj.data.update()


def stitch_curves(obj,shoulders,wrists):
    vertices,faces=geometry(obj)
    loops=boundary_loops(faces)
    material=bpy.data.materials.new('White cotton stitching');material.use_nodes=True
    material.diffuse_color=(.64,.65,.63,1)
    shader=material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=material.diffuse_color
    shader.inputs['Roughness'].default_value=.95
    curves=[]
    for ids in loops:
        points=vertices[ids];center=points.mean(0)
        if center[2]<-.45:
            paths=[points+[0,0,.007],points+[0,0,.011]]
        elif abs(center[0])>.20:
            label='L' if center[0]>0 else 'R'
            axis=wrists[label]-shoulders[label];axis/=np.linalg.norm(axis)
            paths=[points-axis*.006,points-axis*.010]
        else:
            paths=[center+(points-center)*[1.07,1.07,1]+[0,0,.002]]
        for path in paths:
            curve=bpy.data.curves.new('Cotton double stitching','CURVE');curve.dimensions='3D'
            curve.bevel_depth=.0003;curve.bevel_resolution=1
            spline=curve.splines.new('POLY');spline.points.add(len(path)-1)
            for point,coordinate in zip(spline.points,path):point.co=(*coordinate,1)
            spline.use_cyclic_u=True
            seam=bpy.data.objects.new('Stitching',curve);bpy.context.collection.objects.link(seam)
            seam.data.materials.append(material)
            bpy.ops.object.select_all(action='DESELECT');seam.select_set(True)
            bpy.context.view_layer.objects.active=seam;bpy.ops.object.convert(target='MESH')
            curves.append(bpy.context.object)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    for seam in curves:seam.select_set(True)
    bpy.context.view_layer.objects.active=obj;bpy.ops.object.join()


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
    body_vertices=vertices_world(body);body_faces=triangles(body)
    anchor_world={obj.name:obj.matrix_world.copy() for obj in bpy.context.scene.objects if obj.name.startswith('fit_')}
    loaded={}
    for name,entry in source['templates'].items():
        with bpy.data.libraries.load(str((args.models/entry['blend']).resolve()),link=False) as (src,dst):dst.objects=[entry['object']]
        obj=dst.objects[0];bpy.context.collection.objects.link(obj);loaded[entry['kind']]=(name,entry,obj)
    _,entry,top_obj=loaded['crewneck'];pants_name,pants_entry,pants_obj=loaded['slacks']
    placement=anchor_world['fit_anchor'];inverse=placement.inverted()
    body_local=np.array([inverse @ Vector(point) for point in body_vertices])
    shoulders={side:np.array(inverse @ anchor_world['fit_shoulder_'+side].translation) for side in ('L','R')}
    wrists={side:np.array(inverse @ anchor_world['fit_wrist_'+side].translation) for side in ('L','R')}
    anchors={name:np.array(binding['reference']) for name,binding in entry['anchor_bindings'].items()}
    anchors.update(shorten_sleeves(top_obj,shoulders,wrists))
    collar_band(top_obj)
    pants,pants_faces=geometry(pants_obj)
    pants_transform=inverse @ anchor_world['fit_anchor_waist']
    pants_local=np.array([pants_transform @ Vector(point) for point in pants])
    spec=dict(entry['base_spec'],body_length=65.,chest_width=48.,sleeve_length=22.)
    rebuild_info=rebuild_torso(top_obj,(body_local,body_faces),(pants_local,pants_faces),65.,fitted=True,wrinkles=True)
    material=bpy.data.materials.new('Soft white cotton');material.use_nodes=True
    material.diffuse_color=(.80,.81,.79,1)
    shader=material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=material.diffuse_color
    shader.inputs['Roughness'].default_value=.92
    shader.inputs['Specular IOR Level'].default_value=.22
    top_obj.data.materials.clear();top_obj.data.materials.append(material)
    for face in top_obj.data.polygons:face.material_index=0
    stitch_curves(top_obj,shoulders,wrists)
    top,faces=geometry(top_obj)
    top,iterations=clear_body(top,faces,body_local,body_faces,margin=.0025)
    top_obj.data.vertices.foreach_set('co',top.ravel());top_obj.data.update()
    check=inspect(top,faces,body_local,body_faces)
    pair_count=len(tree(top,faces).overlap(tree(pants_local,pants_faces)))
    loops=boundary_loops(faces)
    if pair_count or check['body_triangle_intersections'] or any(check[k]['inside'] for k in ('vertices','edge_midpoints','triangle_centroids')):
        raise ValueError('Body or pants collision remains')
    if len(loops)!=4 or check['topology']['nonmanifold_edges_gt2'] or check['topology']['degenerate_triangles']:
        raise ValueError('Invalid T-shirt opening/topology')
    name='white_crewneck_cc0_v4';models=output/'models';models.mkdir(exist_ok=True)
    for item in list(bpy.context.scene.objects):
        if item!=top_obj:bpy.data.objects.remove(item,do_unlink=True)
    register(top_obj,'crewneck',spec,'shoulder',name,models,25.)
    registry=json.loads((models/'registry.json').read_text())
    registry['templates'][name].update(revision='4',anchor_bindings=save_anchor_bindings(registry['templates'][name],anchors),
        saved_with_blender=bpy.app.version_string,reference_body_sha256=entry['reference_body_sha256'])
    # Keep the already validated trousers with their existing ID.
    import shutil
    for key in ('blend','binding'):shutil.copyfile(args.models/pants_entry[key],models/pants_entry[key])
    registry['templates'][pants_name]=pants_entry
    (models/'registry.json').write_text(json.dumps(registry,indent=2)+'\n')
    report={'style_reference':'User supplied front, side and back white T-shirt images; visual interpretation only',
        'blender_version':bpy.app.version_string,'body_height_input_cm':175,'spec':spec,'torso_rebuild':rebuild_info,
        'body_collision':check,'shirt_pants_triangle_intersections':pair_count,'clearance_iterations':iterations,
        'intentional_openings':len(loops),'template_id':name}
    (output/'tshirt-report.json').write_text(json.dumps(report,indent=2)+'\n')
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    def mesh(name,v,f,color):
        data=bpy.data.meshes.new(name);data.from_pydata(v.tolist(),[],f.tolist());data.update()
        obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
        mat=bpy.data.materials.new(name);mat.diffuse_color=(*color,1);obj.data.materials.append(mat)
        for face in obj.data.polygons:face.use_smooth=True
    mesh('ReferenceBody',body_vertices,body_faces,(.55,.61,.67))
    mesh('WhiteTshirt',np.array([placement @ Vector(point) for point in top]),faces,(.80,.81,.79))
    mesh('Slacks',np.array([anchor_world['fit_anchor_waist'] @ Vector(point) for point in pants]),pants_faces,(.025,.045,.065))
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'reference-fitting.blend'),compress=True)
    print('PASS: reference-style white short sleeve T-shirt registered without body/pants intersection',flush=True)


if __name__=='__main__':main()
