# 역할: 제공된 CC0 의류를 지정 신체 GLB의 어깨·팔 기준에 맞추고 신체 관통을 검사·완화합니다.
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys
import zipfile

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'scripts'))
from geometry.template_binding import geometry
from geometry.garment_cages import cage
from prepare_template import register


def vertices_world(obj):
    return np.array([obj.matrix_world @ vertex.co for vertex in obj.data.vertices])


def triangles(obj):
    obj.data.calc_loop_triangles()
    return np.array([face.vertices[:] for face in obj.data.loop_triangles],dtype=int)


def tree(vertices,faces):
    return BVHTree.FromPolygons(vertices.tolist(),faces.tolist(),all_triangles=True,epsilon=0.)


def signed_points(points,body):
    result=[]
    for point in points:
        nearest,normal,_,_=body.find_nearest(Vector(point))
        result.append(float((Vector(point)-nearest).dot(normal)))
    return np.asarray(result)


def solid_inside(point,body):
    # Closed MHR body: three non-axis ray parity votes disambiguate concave edges.
    votes=0
    for direction in ((.917,.331,.223),(-.271,.883,.384),(.193,-.417,.888)):
        direction=Vector(direction).normalized();origin=Vector(point);hits=0
        for _ in range(128):
            hit,_,_,_=body.ray_cast(origin,direction,10.)
            if hit is None:break
            hits+=1;origin=hit+direction*1e-6
        else:raise ValueError('Solid classification did not converge')
        votes+=hits%2
    return votes>=2


def inspect(vertices,faces,body_vertices,body_faces):
    body=tree(body_vertices,body_faces)
    cloth=tree(vertices,faces)
    edges=np.unique(np.sort(np.vstack([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)
    sample_sets={'vertices':vertices,'edge_midpoints':vertices[edges].mean(axis=1),
                 'triangle_centroids':vertices[faces].mean(axis=1)}
    result={}
    for name,samples in sample_sets.items():
        signed=signed_points(samples,body)
        candidates=np.flatnonzero(signed < -1e-5)
        for index in candidates:
            if not solid_inside(samples[index],body):signed[index]=abs(signed[index])
        result[name]={'samples':len(samples),'inside':int((signed < -1e-5).sum()),
                     'minimum_signed_clearance_mm':float(signed.min()*1000),
                     'normal_negative_candidates':len(candidates),
                     'classification':'nearest normal with 3-ray solid parity for negative candidates'}
    result['body_triangle_intersections']=len(cloth.overlap(body))
    edge_counts=Counter(tuple(sorted(edge)) for row in faces for edge in
                        [(row[0],row[1]),(row[1],row[2]),(row[2],row[0])])
    area=np.linalg.norm(np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],
                                 vertices[faces[:,2]]-vertices[faces[:,0]]),axis=1)/2
    result['topology']={'vertices':len(vertices),'triangles':len(faces),
                        'nonmanifold_edges_gt2':sum(v>2 for v in edge_counts.values()),
                        'boundary_edges':sum(v==1 for v in edge_counts.values()),
                        'degenerate_triangles':int((area<1e-12).sum())}
    return result


def clear_body(vertices,faces,body_vertices,body_faces,margin=.003,minimum_clearance=None,vertex_clearance=None,max_iterations=80):
    body=tree(body_vertices,body_faces)
    result=vertices.copy()
    edges=np.unique(np.sort(np.vstack([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)
    for iteration in range(max_iterations):
        if iteration and iteration%10==0:
            print('FITME_CLEARANCE iteration='+str(iteration),flush=True)
        moved=0
        minimum=float('inf')
        for index,point in enumerate(result):
            nearest,normal,_,_=body.find_nearest(Vector(point))
            distance=(Vector(point)-nearest).dot(normal)
            minimum=min(minimum,distance)
            target=margin if vertex_clearance is None else float(vertex_clearance[index])
            if distance < target-1e-6:
                result[index]=np.array(nearest+normal*target)
                moved+=1
        delta=np.zeros_like(result)
        count=np.zeros(len(result))
        for groups in (edges,faces):
            for ids in groups:
                point=result[ids].mean(axis=0)
                nearest,normal,_,_=body.find_nearest(Vector(point))
                distance=(Vector(point)-nearest).dot(normal)
                minimum=min(minimum,distance)
                if distance < .0015-1e-5:
                    delta[ids]+=np.asarray(normal)*(.0015-distance)
                    count[ids]+=1
                    moved+=1
        overlaps=tree(result,faces).overlap(body)
        if not overlaps and (moved==0 or minimum_clearance is not None and minimum>=minimum_clearance):
            break
        for cloth_index,body_index in overlaps:
            ids=faces[cloth_index]
            q=body_vertices[body_faces[body_index]]
            normal=np.cross(q[1]-q[0],q[2]-q[0])
            normal/=np.linalg.norm(normal)
            depth=margin-float(((result[ids]-q[0]) @ normal).min())
            if depth > 0:
                shift=normal*min(depth,.015)
                delta[ids]+=shift
                count[ids]+=1
        active=count>0
        result[active]+=delta[active]/count[active,None]
    return result,iteration+1


def boundary_loops(faces):
    counts=Counter(tuple(sorted(edge)) for row in faces for edge in
                   [(row[0],row[1]),(row[1],row[2]),(row[2],row[0])])
    adjacent={}
    for (a,b),count in counts.items():
        if count==1:
            adjacent.setdefault(a,set()).add(b);adjacent.setdefault(b,set()).add(a)
    remaining=set(adjacent);loops=[]
    while remaining:
        stack=[remaining.pop()];loop=[]
        while stack:
            vertex=stack.pop();loop.append(vertex)
            for other in adjacent[vertex]&remaining:
                remaining.remove(other);stack.append(other)
        loops.append(np.array(loop,dtype=int))
    return loops


def gltf_point(point):
    x,y,z=point
    return [float(x),float(z),float(-y)]


def save_anchor_bindings(entry,anchors):
    reference,faces,_,_=cage(entry['kind'],entry['base_spec'],entry['sleeve_basis'])
    bvh=tree(reference,faces)
    result={}
    for name,point in anchors.items():
        nearest,_,face,_=bvh.find_nearest(Vector(point))
        ids=faces[face]
        a,b,c=reference[ids]
        uv=np.linalg.lstsq(np.column_stack((b-a,c-a)),np.asarray(nearest)-a,rcond=None)[0]
        weights=np.clip([1-uv.sum(),uv[0],uv[1]],0,1)
        weights/=weights.sum()
        result[name]={'reference':list(map(float,point)),'ids':ids.tolist(),'weights':weights.tolist()}
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--archive',required=True,type=Path)
    parser.add_argument('--body',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    output=args.output.resolve()
    output.mkdir(parents=True,exist_ok=True)
    source=output/'source';source.mkdir(exist_ok=True)
    with zipfile.ZipFile(args.archive) as archive:
        prefix='FitMe_CC0_Garments/'
        registry=json.loads(archive.read(prefix+'model/registry.json'))
        for entry in registry['templates'].values():
            name=entry['blend']
            if Path(name).name!=name:raise ValueError('Unexpected model path')
            (source/name).write_bytes(archive.read(prefix+'model/'+name))
        (output/'SOURCES.md').write_bytes(archive.read(prefix+'licenses/SOURCES.md'))
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(args.body.resolve()))
    body_obj=next(obj for obj in bpy.context.scene.objects if obj.type=='MESH')
    body_vertices=vertices_world(body_obj);body_faces=triangles(body_obj)
    anchor_world={obj.name:obj.matrix_world.copy() for obj in bpy.context.scene.objects if obj.name.startswith('fit_')}
    models=output/'models';models.mkdir(exist_ok=True)
    report={'reference_body_sha256':hashlib.sha256(args.body.read_bytes()).hexdigest(),
            'reference_height_cm':float(np.ptp(body_vertices[:,2])*100),'clearance_target_mm':3.,'garments':{}}
    displayed=[]
    for old_id,entry in registry['templates'].items():
        kind=entry['kind']
        new_id=old_id.replace('_v1','_v2')
        root_name='fit_anchor' if kind=='crewneck' else 'fit_anchor_waist'
        placement=anchor_world[root_name]
        inverse=placement.inverted()
        local_body=np.array([inverse @ Vector(point) for point in body_vertices])
        with bpy.data.libraries.load(str(source/entry['blend']),link=False) as (src,dst):
            dst.objects=[entry['object']]
        obj=dst.objects[0];bpy.context.collection.objects.link(obj)
        initial,faces=geometry(obj)
        before=inspect(initial,faces,local_body,body_faces)
        spec=dict(entry['base_spec'])
        anchors={root_name:np.zeros(3)}
        if kind=='crewneck':
            shoulders={side:np.array(inverse @ anchor_world['fit_shoulder_'+side].translation) for side in ('L','R')}
            wrists={side:np.array(inverse @ anchor_world['fit_wrist_'+side].translation) for side in ('L','R')}
            width=float(np.linalg.norm(shoulders['L']-shoulders['R']))
            spec['garment_shoulder_width']=width*100
            spec['sleeve_length']=float(np.mean([np.linalg.norm(wrists[s]-shoulders[s]) for s in shoulders])*100)
            adjusted=initial.copy()
            influence=np.clip((initial[:,2]+.22)/.22,0,1)
            influence=influence*influence*(3-2*influence)
            adjusted[:,0]*=1-influence*(1-width/(entry['base_spec']['garment_shoulder_width']/100))
            for label,side in [('L',1),('R',-1)]:
                origin=np.array([side*entry['base_spec']['garment_shoulder_width']/200,0,0])
                old_axis=np.array([side*math.sin(math.pi/4),-.11,-math.cos(math.pi/4)])
                old_axis/=np.linalg.norm(old_axis)
                new_axis=wrists[label]-shoulders[label]
                new_length=np.linalg.norm(new_axis);new_axis/=new_length
                rotation=Vector(old_axis).rotation_difference(Vector(new_axis)).to_matrix()
                relative=initial-origin
                along=relative @ old_axis
                perpendicular=relative-along[:,None]*old_axis
                transformed=shoulders[label]+np.array([rotation @ Vector(point) for point in perpendicular])
                transformed+=along[:,None]*(new_length/(entry['base_spec']['sleeve_length']/100))*new_axis
                influence=np.clip((side*initial[:,0]-(abs(origin[0])-.08))/.08,0,1)
                influence=influence*influence*(3-2*influence)
                adjusted=adjusted*(1-influence[:,None])+transformed*influence[:,None]
                anchors['fit_shoulder_'+label]=shoulders[label]
                anchors['fit_cuff_'+label]=wrists[label]
            loops=boundary_loops(faces)
            for label,side in [('L',1),('R',-1)]:
                cuff=max(loops,key=lambda ids:side*adjusted[ids,0].mean())
                offset=wrists[label]-adjusted[cuff].mean(axis=0)
                source_shoulder=np.array([side*entry['base_spec']['garment_shoulder_width']/200,0,0])
                old_axis=np.array([side*math.sin(math.pi/4),-.11,-math.cos(math.pi/4)])
                old_axis/=np.linalg.norm(old_axis)
                progress=(initial-source_shoulder) @ old_axis/(entry['base_spec']['sleeve_length']/100)
                influence=np.clip((progress-.65)/.3,0,1)*(side*initial[:,0]>0)
                influence=influence*influence*(3-2*influence)
                adjusted+=influence[:,None]*offset
        else:
            adjusted=initial.copy()
            # Compatibility alias for existing web GLB composition.
            anchors['fit_anchor']=np.zeros(3)
            _,_,base_anchors,_=cage(kind,spec,entry['sleeve_basis'])
            for item in base_anchors:
                if item['name']!=root_name:
                    x,z,minus_y=item['translation'];anchors[item['name']]=np.array([x,-minus_y,z])
        aligned=inspect(adjusted,faces,local_body,body_faces)
        corrected,iterations=clear_body(adjusted,faces,local_body,body_faces)
        after=inspect(corrected,faces,local_body,body_faces)
        if (after['body_triangle_intersections'] or any(after[key]['inside'] for key in
                ('vertices','edge_midpoints','triangle_centroids')) or after['topology']['degenerate_triangles']):
            raise ValueError('Reference collision or topology validation failed; no final template published')
        alignment={}
        if kind=='crewneck':
            cloth_tree=tree(corrected,faces)
            body_tree=tree(local_body,body_faces)
            for label,side in [('L',1),('R',-1)]:
                cuff=max(boundary_loops(faces),key=lambda ids:side*corrected[ids,0].mean())
                center=corrected[cuff].mean(axis=0)
                axis=center-shoulders[label];axis/=np.linalg.norm(axis)
                expected=wrists[label]-shoulders[label];expected/=np.linalg.norm(expected)
                nearest,_,_,_=cloth_tree.find_nearest(Vector(shoulders[label]))
                body_nearest,_,_,_=body_tree.find_nearest(Vector(shoulders[label]))
                cloth_nearest,_,_,_=cloth_tree.find_nearest(body_nearest)
                alignment[label]={'shoulder_anchor_error_mm':0.,
                    'cuff_center_error_mm':float(np.linalg.norm(center-wrists[label])*1000),
                    'sleeve_axis_error_deg':float(np.degrees(np.arccos(np.clip(axis @ expected,-1,1)))),
                    'nearest_shoulder_surface_offset_mm':((np.asarray(nearest)-shoulders[label])*1000).tolist(),
                    'body_surface_offset_from_shoulder_anchor_mm':((np.asarray(body_nearest)-shoulders[label])*1000).tolist(),
                    'shoulder_surface_gap_mm':float((cloth_nearest-body_nearest).length*1000)}
        obj.data.vertices.foreach_set('co',corrected.ravel());obj.data.update()
        # Store only this garment in its source blend; use identity transforms.
        for item in list(bpy.context.scene.objects):
            if item!=obj:bpy.data.objects.remove(item,do_unlink=True)
        registration=register(obj,kind,spec,entry['sleeve_basis'],new_id,models,max_distance_cm=25.)
        current=json.loads((models/'registry.json').read_text())
        current['templates'][new_id]['revision']='2'
        current['templates'][new_id]['anchor_bindings']=save_anchor_bindings(current['templates'][new_id],anchors)
        current['templates'][new_id]['reference_body_sha256']=report['reference_body_sha256']
        (models/'registry.json').write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        report['garments'][new_id]={'before':before,'after_alignment':aligned,'after':after,'iterations':iterations,
            'maximum_collision_correction_cm':float(np.linalg.norm(corrected-adjusted,axis=1).max()*100),
            'base_spec':spec,'registration':registration,'anchors_blender_m':{name:point.tolist() for name,point in anchors.items()}}
        report['garments'][new_id]['alignment']=alignment
        displayed.append((new_id,corrected,faces,placement.copy()))
        print('FITME_REBUILD '+json.dumps({'id':new_id,'after':after}),flush=True)
    (output/'collision-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # A combined inspectable scene keeps the tested placement and reference body.
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    def mesh(name,vertices,faces,color):
        data=bpy.data.meshes.new(name);data.from_pydata(vertices.tolist(),[],faces.tolist());data.update()
        obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
        material=bpy.data.materials.new(name);material.diffuse_color=(*color,1);obj.data.materials.append(material)
        for face in obj.data.polygons:face.use_smooth=True
        return obj
    mesh('ReferenceBody',body_vertices,body_faces,(.65,.72,.78))
    for name,vertices,faces,placement in displayed:
        mesh(name,np.array([placement @ Vector(point) for point in vertices]),faces,(.025,.045,.065))
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'reference-fitting.blend'),compress=True)


if __name__=='__main__':
    main()
