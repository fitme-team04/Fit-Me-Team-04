# 역할: 등록 의류 메시와 케이지를 연결하고 정점 변형을 적용합니다.
"""Blender-side registration and deformation of static garment meshes."""
import hashlib
import json
import numpy as np
import bpy
from pathlib import Path
from functools import lru_cache
from contextlib import contextmanager
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from geometry.garment_cages import cage, CAGE_VERSION
from geometry.glb import to_gltf


@lru_cache(maxsize=8)
def cached_binding(path):
    with np.load(path,allow_pickle=False) as data:
        result={key:np.array(data[key],copy=True) for key in data.files}
    for array in result.values():array.setflags(write=False)
    return result


@contextmanager
def binding_data(path):
    yield cached_binding(str(Path(path).resolve()))


def geometry(obj):
    if obj.type!='MESH' or obj.modifiers or obj.data.shape_keys:
        raise ValueError('Template must be a prepared static mesh; run prepare_template.py')
    if not np.allclose(np.array(obj.matrix_world),np.eye(4),atol=1e-7):
        raise ValueError('Prepared template transforms must be identity')
    obj.data.calc_loop_triangles()
    return (np.array([v.co[:] for v in obj.data.vertices]),
            np.array([t.vertices[:] for t in obj.data.loop_triangles],dtype=np.int64))


def digest(vertices,faces):
    h=hashlib.sha256()
    h.update(np.asarray(vertices,dtype='<f4').tobytes())
    h.update(np.asarray(faces,dtype='<i4').tobytes())
    return h.hexdigest()


def bind(obj,kind,spec,basis,path,max_distance_cm=8):
    vertices,faces=geometry(obj)
    ref,tri,_,_=cage(kind,spec,basis)
    tree=BVHTree.FromPolygons([Vector(v) for v in ref],tri.tolist(),all_triangles=True)
    ids=[];weights=[];distances=[]
    for point in vertices:
        closest,_,index,distance=tree.find_nearest(Vector(point))
        if index is None:raise ValueError('Could not bind a garment vertex')
        a,b,c=ref[tri[index]]
        v0,v1,v2=b-a,c-a,np.array(closest)-a
        d00,d01,d11=np.dot(v0,v0),np.dot(v0,v1),np.dot(v1,v1)
        d20,d21=np.dot(v2,v0),np.dot(v2,v1)
        denominator=d00*d11-d01*d01
        w1=(d11*d20-d01*d21)/denominator
        w2=(d00*d21-d01*d20)/denominator
        w=np.clip([1-w1-w2,w1,w2],0,1);w/=w.sum()
        ids.append(tri[index]);weights.append(w);distances.append(distance*100)
    distances=np.asarray(distances)
    if distances.max()>max_distance_cm:
        raise ValueError(f'Template alignment/baseline mismatch: max cage distance {distances.max():.2f} cm')
    np.savez_compressed(path,schema_version=1,cage_version=CAGE_VERSION,
        reference=ref,reference_faces=tri,ids=np.array(ids),weights=np.array(weights),
        geometry_hash=digest(vertices,faces),kind=kind,base_spec_json=json.dumps(spec,sort_keys=True),
        sleeve_basis=basis)
    return {'vertices':len(vertices),'triangles':len(faces),
            'distance_cm':{'median':float(np.median(distances)),
                           'p95':float(np.percentile(distances,95)),'max':float(distances.max())}}


def static_template(obj,entry):
    # 역할: 하의 원본 정점과 등록 기준점을 치수 변형 없이 반환합니다.
    vertices,faces=geometry(obj)
    with binding_data(entry['binding_path']) as binding:
        baseline=json.loads(str(binding['base_spec_json']))
    _,_,base_anchors,_=cage('slacks',baseline,'none')
    points={anchor['name']:np.array([anchor['translation'][0],-anchor['translation'][2],anchor['translation'][1]])
            for anchor in base_anchors}
    points.update({name:np.asarray(binding['reference'],dtype=float)
                   for name,binding in entry.get('anchor_bindings',{}).items()})
    points.setdefault('fit_anchor_waist',np.zeros(3))
    anchors=[{'name':name,'translation':to_gltf(point[None,:])[0].tolist()} for name,point in points.items()]
    return anchors,{}, {'template_vertices':len(vertices),'template_triangles':len(faces),
                       'source_geometry_sha256':digest(vertices,faces),
                       'deformation_applied':False,'geometry_mode':'static'}


def body_template(obj,entry):
    # 역할: SAM 피팅에는 상품 DB 치수 변형 없이 검증한 원형과 원래 기준점만 제공합니다.
    from geometry.mesh_validation import validate_mesh
    vertices,faces=geometry(obj)
    source_hash=digest(vertices,faces)
    quality=validate_mesh(vertices.tolist(),faces.tolist())
    with binding_data(entry['binding_path']) as binding:
        if int(binding['schema_version'])!=1 or int(binding['cage_version'])!=CAGE_VERSION:
            raise ValueError('Binding version mismatch; prepare the template again')
        if str(binding['kind'])!=entry['kind'] or str(binding['geometry_hash'])!=source_hash:
            raise ValueError('Template geometry changed; prepare the template again')
        baseline=json.loads(str(binding['base_spec_json']))
        _,_,base_anchors,_=cage(entry['kind'],baseline,str(binding['sleeve_basis']))
    points={anchor['name']:np.array([anchor['translation'][0],-anchor['translation'][2],anchor['translation'][1]])
            for anchor in base_anchors}
    for name,binding in entry.get('anchor_bindings',{}).items():
        position=np.asarray(binding['reference'],dtype=float)
        if name not in set(points)|{'fit_anchor'} or position.shape!=(3,) or not np.isfinite(position).all():
            raise ValueError('Invalid reference anchor binding')
        points[name]=position
    points.setdefault('fit_anchor_waist' if entry['kind']=='slacks' else 'fit_anchor',np.zeros(3))
    anchors=[{'name':name,'translation':to_gltf(point[None,:])[0].tolist()} for name,point in points.items()]
    return anchors,{}, {'template_vertices':len(vertices),'template_triangles':len(faces),
                       'source_geometry_sha256':source_hash,'source_mesh_quality':quality,
                       'reference_mesh_quality':quality,'deformation_applied':False,'geometry_mode':'sam_body'}


def deform(obj,entry,spec,basis):
    if entry['kind']=='slacks':
        return static_template(obj,entry)
    from geometry.mesh_validation import validate_mesh
    vertices,faces=geometry(obj)
    source_quality=validate_mesh(vertices.tolist(),faces.tolist())
    with binding_data(entry['binding_path']) as b:
        if int(b['schema_version'])!=1 or int(b['cage_version'])!=CAGE_VERSION:
            raise ValueError('Binding version mismatch; prepare the template again')
        if str(b['kind'])!=entry['kind'] or str(b['geometry_hash'])!=digest(vertices,faces):
            raise ValueError('Template geometry changed; prepare the template again')
        reference=np.asarray(b['reference'])
        baseline=json.loads(str(b['base_spec_json']))
        if entry.get('deformation_policy')=='regenerate_four_input_ratios' and any(abs(float(spec[k])-float(v))>1e-7 for k,v in baseline.items()):
            raise ValueError('This template preserves fixed ratios: regenerate with build_body_proportional_shirt.py --spec-json instead of cage deformation')
        check,check_tri,_,_=cage(entry['kind'],baseline,str(b['sleeve_basis']))
        target_spec = spec
        target,tri,anchors,metrics=cage(entry['kind'],target_spec,basis)
        metrics = {key:value for key,value in metrics.items() if key in spec}
        if not np.allclose(reference,check,atol=1e-9) or not np.array_equal(check_tri,b['reference_faces']) or not np.array_equal(tri,check_tri):
            raise ValueError('Cage topology changed; rebind the template')
        ids=np.asarray(b['ids']);weights=np.asarray(b['weights'])
        if ids.shape!=(len(vertices),3) or weights.shape!=ids.shape or ids.dtype.kind not in 'iu':
            raise ValueError('Invalid template binding dimensions')
        if ids.min()<0 or ids.max()>=len(reference) or not np.isfinite(weights).all() or np.any(weights<0) or not np.allclose(weights.sum(1),1):
            raise ValueError('Invalid template binding values')
        moved=vertices+np.einsum('vij,vi->vj',(target-reference)[ids],weights)
    shape_anchors = None
    if entry.get('deformation_policy') in ('shape_preserving_four_inputs_v1','shape_preserving_center_back_v1'):
        from geometry.shirt_shape import reshape
        moved, shape_anchors = reshape(vertices, entry, baseline, spec, basis)
        before = np.cross(vertices[faces[:,1]]-vertices[faces[:,0]], vertices[faces[:,2]]-vertices[faces[:,0]])
        after = np.cross(moved[faces[:,1]]-moved[faces[:,0]], moved[faces[:,2]]-moved[faces[:,0]])
        if np.any(np.linalg.norm(after,axis=1)<1e-12) or np.any(np.einsum('ij,ij->i',before,after)<=0):
            raise ValueError('Shirt deformation would collapse or invert triangles')
    if not np.isfinite(moved).all():raise ValueError('Non-finite deformed vertices')
    obj.data.vertices.foreach_set('co',moved.ravel())
    obj.data.update()
    # Rebuilt templates may place their seam/cuff anchors on a reference body.
    # Bind these anchors to the same cage displacement as the garment surface.
    if entry.get('anchor_bindings'):
        by_name={anchor['name']:anchor for anchor in anchors}
        allowed=set(by_name)|{'fit_anchor'}
        for name,binding in entry['anchor_bindings'].items():
            position=np.asarray(binding['reference'],dtype=float)
            anchor_ids=np.asarray(binding['ids'])
            anchor_weights=np.asarray(binding['weights'],dtype=float)
            if (name not in allowed or position.shape!=(3,) or anchor_ids.shape!=(3,)
                    or anchor_ids.dtype.kind not in 'iu' or anchor_ids.min()<0 or anchor_ids.max()>=len(reference)
                    or anchor_weights.shape!=(3,) or not np.isfinite(position).all()
                    or not np.isfinite(anchor_weights).all() or np.any(anchor_weights<0)
                    or not np.isclose(anchor_weights.sum(),1)):
                raise ValueError('Invalid reference anchor binding')
            point=position+anchor_weights @ (target-reference)[anchor_ids]
            by_name[name]={'name':name,'translation':to_gltf(point[None,:])[0].tolist()}
        anchors=list(by_name.values())
    if shape_anchors is not None:
        anchors = [{'name':name,'translation':to_gltf(point[None,:])[0].tolist()} for name,point in shape_anchors.items()]
    info = {'template_vertices':len(vertices),'template_triangles':len(faces),
            'source_mesh_quality':source_quality,
            'db_mesh_quality':validate_mesh(moved.tolist(),faces.tolist(),vertices.tolist()),
            'source_geometry_sha256':digest(vertices,faces)}
    return anchors,metrics,info
