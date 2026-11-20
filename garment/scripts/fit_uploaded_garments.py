# 역할: 첨부 의류를 기본 신체 A 자세에 맞춰 변형·등록합니다. 신체 충돌만 보정하고 상하의 상호 충돌은 계산하지 않습니다.
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Matrix,Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from geometry.template_binding import geometry
from prepare_template import register
from rebuild_cc0_reference import vertices_world,triangles,tree,inspect,clear_body,save_anchor_bindings
from build_reference_wide_slacks import profile


def load_static(path):
    before=set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path.resolve()),merge_vertices=True)
    objects=[obj for obj in set(bpy.context.scene.objects)-before if obj.type=='MESH']
    if len(objects)!=1:raise ValueError('Expected one garment mesh in supplied GLB')
    obj=objects[0];bpy.context.view_layer.update()
    obj.data.transform(obj.matrix_world);obj.parent=None;obj.matrix_world=Matrix.Identity(4)
    bm=bmesh.new();bm.from_mesh(obj.data)
    # Only the supplied shirt's two tiny triangular scan holes are repaired.
    boundary=[edge for edge in bm.edges if edge.is_boundary]
    if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=6)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    if obj.data.has_custom_normals:
        obj.data.normals_split_custom_set(np.zeros((len(obj.data.loops),3)).tolist())
    for face in obj.data.polygons:face.use_smooth=True
    return obj


def smooth(value):
    value=np.clip(value,0,1)
    return value*value*(3-2*value)


def fit_shirt(vertices,faces,anchors,arm_separation=.26,cuff_height=.035):
    from scipy import sparse
    from scipy.sparse.csgraph import connected_components
    root=anchors['fit_anchor'];inverse=root.inverted()
    shoulders={side:np.array(inverse @ anchors['fit_shoulder_'+side].translation) for side in ('L','R')}
    wrists={side:np.array(inverse @ anchors['fit_wrist_'+side].translation) for side in ('L','R')}
    lower=smooth((.56-vertices[:,2])/.42)
    torso=vertices-np.array([0.,.02,.86])
    torso[:,0]*=.80+.10*lower
    torso[:,1]*=.65+.07*lower+.08*np.exp(-((vertices[:,2]-.36)/.20)**2)
    torso[:,2]*=.71
    result=torso.copy();bindings={'fit_anchor':np.zeros(3)}
    edges=np.unique(np.sort(np.vstack((faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]])),axis=1),axis=0)
    graph=sparse.coo_matrix((np.ones(len(edges)*2),(np.r_[edges[:,0],edges[:,1]],np.r_[edges[:,1],edges[:,0]])),
                           shape=(len(vertices),len(vertices))).tocsr()
    degree=np.maximum(1,np.asarray(graph.sum(1)).ravel())
    for label,side in [('L',1),('R',-1)]:
        source_shoulder=np.array([side*.29,.02,.86])
        source_cuff=np.array([side*.424,-.032,cuff_height])
        old_axis=source_cuff-source_shoulder;old_length=np.linalg.norm(old_axis);old_axis/=old_length
        new_axis=wrists[label]-shoulders[label];new_length=np.linalg.norm(new_axis);new_axis/=new_length
        rotation=Vector(old_axis).rotation_difference(Vector(new_axis)).to_matrix()
        relative=vertices-source_shoulder;distance=relative @ old_axis
        perpendicular=relative-distance[:,None]*old_axis
        radius_scale=.88-.18*np.clip(distance/old_length,0,1)
        moved=shoulders[label]+np.array([rotation @ Vector(point) for point in perpendicular])*radius_scale[:,None]
        moved+=distance[:,None]/old_length*new_length*new_axis
        ids=np.flatnonzero((vertices[:,2]<.62)&(side*vertices[:,0]>arm_separation))
        _,components=connected_components(graph[ids][:,ids],directed=False)
        seed=np.argmin(np.linalg.norm(vertices[ids]-source_cuff,axis=1))
        fixed_arm=ids[components==components[seed]]
        weight=smooth((side*vertices[:,0]-.20)/.14)*smooth((vertices[:,2]-.56)/.12)
        weight[fixed_arm]=1.
        fixed_body=(np.abs(vertices[:,0])<.20)|((vertices[:,2]<.60)&(np.abs(vertices[:,0])<arm_separation-.005))
        for _ in range(8):
            weight=.5*weight+.5*(graph @ weight)/degree
            weight[fixed_arm]=1.;weight[fixed_body]=0.
        result=result*(1-weight[:,None])+moved*weight[:,None]
        bindings['fit_shoulder_'+label]=shoulders[label]
        bindings['fit_cuff_'+label]=wrists[label]
    return result,bindings


def fit_pants(vertices,faces,body_vertices,body_faces):
    old_z=vertices[:,2]
    hem=float(body_vertices[:,2].min()+.05)
    result=vertices.copy()
    result[:,2]=np.interp(old_z,[0.,.02,.735,.98,1.02],[hem-.006,hem,-.27,0.,.04])
    upper_scale=1.12+.06*smooth((old_z-.82)/.12)
    result[:,:2]*=upper_scale[:,None]
    grid=np.linspace(max(.04,float(vertices[:,2].min())+.01),.70,100)
    for label,side in [('L',1),('R',-1)]:
        old_profiles=np.array([profile(vertices,faces,z,side) for z in grid])
        thigh=profile(body_vertices,body_faces,-.34,side)
        ankle=profile(body_vertices,body_faces,-.87,side)
        ids=np.flatnonzero((side*vertices[:,0]>0)&(old_z<.72))
        source=np.column_stack([np.interp(old_z[ids],grid,old_profiles[:,k]) for k in range(4)])
        progress=np.clip((-.27-result[ids,2])/(-.27-hem),0,1)
        center=(1-progress[:,None])*thigh[:2]+progress[:,None]*ankle[:2]
        center[:,0]+=side*.006
        radii=np.maximum(source[:,2:]*1.12,((1-progress[:,None])*thigh[2:]+progress[:,None]*ankle[2:])+.018)
        radii[:,0]=np.minimum(radii[:,0],np.abs(center[:,0])-.0008)
        normalized=(vertices[ids,:2]-source[:,:2])/np.maximum(source[:,2:],.001)
        mapped=center+normalized*radii
        weight=smooth((.735-old_z[ids])/.075)
        result[ids,:2]=result[ids,:2]*(1-weight[:,None])+mapped*weight[:,None]
    # Bare-foot instep clearance: lift only low cuff points that would enter
    # the heel/foot, retaining the source's folds and all UV coordinates.
    foot_faces=body_faces[body_vertices[body_faces,2].max(axis=1)<-.86]
    foot=tree(body_vertices,foot_faces)
    for index in np.flatnonzero(result[:,2]<-.88):
        x,y,z=result[index]
        hit,_,_,_=foot.ray_cast(Vector((x,y,-.85)),Vector((0,0,-1)),.3)
        if hit is not None and z<hit.z+.007:result[index,2]=hit.z+.007
    # Keep the inner rear crotch fabric between the thighs rather than pressing
    # it into either thigh. The smooth, sign-preserving warp retains UVs.
    inner=np.exp(-(result[:,0]/.065)**4)*np.exp(-((result[:,2]+.32)/.075)**4)
    inner*=smooth((result[:,1]+.01)/.025)
    result[:,0]*=1-.55*inner
    return result


def shell_clearances(vertices,faces,body_vertices,body_faces):
    normals=np.zeros_like(vertices)
    face_normals=np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],vertices[faces[:,2]]-vertices[faces[:,0]])
    for corner in range(3):np.add.at(normals,faces[:,corner],face_normals)
    normals/=np.maximum(np.linalg.norm(normals,axis=1),1e-12)[:,None]
    body=tree(body_vertices,body_faces)
    # The material is a closed thin shell, not a single sheet. Keep the outer
    # surface farther from the skin than the inward-facing lining.
    return np.array([.005+.002*float(np.clip(normals[i] @ np.array(body.find_nearest(Vector(point))[1]),-1,1))
                     for i,point in enumerate(vertices)])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--shirt',required=True,type=Path)
    parser.add_argument('--pants',required=True,type=Path)
    parser.add_argument('--body',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--arm-separation',type=float,default=.26)
    parser.add_argument('--cuff-height',type=float,default=.035)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(args.body.resolve()))
    body=next(obj for obj in bpy.context.scene.objects if obj.type=='MESH')
    world_body=vertices_world(body);body_faces=triangles(body)
    anchors={obj.name:obj.matrix_world.copy() for obj in bpy.context.scene.objects if obj.name.startswith('fit_')}
    shirt_obj=load_static(args.shirt);pants_obj=load_static(args.pants)
    shirt_original,shirt_faces=geometry(shirt_obj);pants_original,pants_faces=geometry(pants_obj)
    shirt_placement=anchors['fit_anchor'];pants_placement=anchors['fit_anchor_waist']
    shirt_body=np.array([shirt_placement.inverted() @ Vector(point) for point in world_body])
    pants_body=np.array([pants_placement.inverted() @ Vector(point) for point in world_body])
    shirt,shirt_anchors=fit_shirt(shirt_original,shirt_faces,anchors,args.arm_separation,args.cuff_height)
    pants=fit_pants(pants_original,pants_faces,pants_body,body_faces)
    report={'reference_height_input_cm':175,'reference_body_sha256':hashlib.sha256(args.body.read_bytes()).hexdigest(),
        'blender_version':bpy.app.version_string,'sources':{path.name:{'bytes':path.stat().st_size,
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for path in [args.shirt,args.pants]},'garments':{}}
    prepared=[]
    for name,kind,obj,vertices,faces,placement,body_local,spec,bindings in [
        ('uploaded_longsleeve_v6','crewneck',shirt_obj,shirt,shirt_faces,shirt_placement,shirt_body,
         {'body_length':70.,'garment_shoulder_width':37.2,'chest_width':53.,'sleeve_length':49.37},shirt_anchors),
        ('uploaded_dress_slacks_v6','slacks',pants_obj,pants,pants_faces,pants_placement,pants_body,
         {'waist_width':42.,'hip_width':50.,'front_rise':30.,'inseam':72.,'thigh_width':31.,'knee_width':23.,'hem_width':19.},
         {'fit_anchor_waist':np.zeros(3),'fit_anchor':np.zeros(3),'fit_crotch':np.array([0.,0.,-.27]),
          'fit_hem_L':np.array([.12,0.,float(pants_body[:,2].min()+.05)]),'fit_hem_R':np.array([-.12,0.,float(pants_body[:,2].min()+.05)])})]:
        before=inspect(vertices,faces,body_local,body_faces)
        targets=shell_clearances(vertices,faces,body_local,body_faces)
        corrected,iterations=clear_body(vertices,faces,body_local,body_faces,margin=.003,
            minimum_clearance=.0012,vertex_clearance=targets,max_iterations=15)
        for refinement in range(4):
            pairs=tree(corrected,faces).overlap(tree(body_local,body_faces))
            if not pairs:break
            obj.data.vertices.foreach_set('co',corrected.ravel());obj.data.update();obj.data.calc_loop_triangles()
            polygons={obj.data.loop_triangles[i].polygon_index for i,_ in pairs}
            bm=bmesh.new();bm.from_mesh(obj.data);bm.faces.ensure_lookup_table()
            edges=set(e for i in polygons for e in bm.faces[i].edges)
            bmesh.ops.subdivide_edges(bm,edges=list(edges),cuts=1,use_grid_fill=True)
            bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free();obj.data.update()
            corrected,faces=geometry(obj)
            targets=shell_clearances(corrected,faces,body_local,body_faces)
            corrected,extra=clear_body(corrected,faces,body_local,body_faces,margin=.003,
                minimum_clearance=.0012,vertex_clearance=targets,max_iterations=15)
            iterations+=extra
            print('FITME_LOCAL_REFINEMENT '+json.dumps({'pass':refinement+1,'vertices':len(corrected)}),flush=True)
        after=inspect(corrected,faces,body_local,body_faces)
        if after['body_triangle_intersections'] or any(after[k]['inside'] for k in ('vertices','edge_midpoints','triangle_centroids')):
            np.savez_compressed(output/(name+'-diagnostic.npz'),vertices=corrected,faces=faces,
                                body_vertices=body_local,body_faces=body_faces)
            print('FITME_FAILED_CHECK '+json.dumps(after),flush=True)
            raise ValueError('Body intersection remains: '+name)
        if after['topology']['degenerate_triangles'] or after['topology']['nonmanifold_edges_gt2']:
            raise ValueError('Invalid fitted source topology: '+name)
        obj.data.vertices.foreach_set('co',corrected.ravel());obj.data.update()
        from scipy.spatial import cKDTree
        correction=np.linalg.norm(corrected-vertices,axis=1) if len(corrected)==len(vertices) else cKDTree(vertices).query(corrected)[0]
        report['garments'][name]={'before':before,'after':after,'clearance_iterations':iterations,
            'maximum_clearance_correction_cm':float(correction.max()*100),
            'correction_metric':'vertex displacement' if len(corrected)==len(vertices) else 'nearest original surface vertex distance after subdivision',
            'material_slots':len(obj.data.materials),'uv_layers':len(obj.data.uv_layers)}
        prepared.append((name,kind,obj,corrected,faces,placement,spec,bindings))
        print('PASS: fitted source '+name,flush=True)
    report['garment_pair_collision']={'checked':False,'corrected':False}
    models=output/'models';models.mkdir(exist_ok=True)
    for name,kind,obj,vertices,faces,placement,spec,bindings in prepared:
        hidden=[(item,list(item.users_collection)) for item in bpy.context.scene.objects if item!=obj]
        for item,collections in hidden:
            item.name='HiddenSource_'+item.name
            for collection in collections:collection.objects.unlink(item)
        register(obj,kind,spec,'shoulder' if kind=='crewneck' else 'none',name,models,30.)
        path=models/'registry.json';registry=json.loads(path.read_text())
        registry['templates'][name].update(revision='6',anchor_bindings=save_anchor_bindings(registry['templates'][name],bindings),
            saved_with_blender=bpy.app.version_string,reference_body_sha256=report['reference_body_sha256'])
        path.write_text(json.dumps(registry,indent=2)+'\n')
        for item,collections in hidden:
            for collection in collections:collection.objects.link(item)
    (output/'fitting-report.json').write_text(json.dumps(report,indent=2)+'\n')
    # Keep the imported materials and packed image textures in the inspection scene.
    for obj,placement in [(shirt_obj,shirt_placement),(pants_obj,pants_placement)]:obj.matrix_world=placement
    for name,kind,obj,*_ in prepared:obj.name='UploadedShirt' if kind=='crewneck' else 'UploadedPants'
    body.name='ReferenceBody'
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'reference-fitting.blend'),compress=True)
    print('PASS: both uploaded garments fitted; body intersections=0; garment pair collision skipped',flush=True)


if __name__=='__main__':main()
