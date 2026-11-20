# 역할: 등록 의류를 SAM 피팅 원형 또는 상품 실측 크기로 준비하고 GLB로 내보냅니다.
"""Prepare registered geometry for SAM fitting or catalog sizing, then export GLB."""
import json
import os
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bpy
from geometry.glb import pack,unpack
from geometry.template_catalog import resolve_template
from geometry.template_binding import deform, body_template
from geometry.cloth_fit import simulate, stage
from core.garment_specs import validate_spec

TEMPLATE_OBJECTS = {}


def load_template(entry):
    # 역할: 상주 Blender에서 템플릿을 한 번 로딩하고 매 요청에는 메시 사본만 제공합니다.
    key=entry['template_id']
    if key not in TEMPLATE_OBJECTS:
        with bpy.data.libraries.load(entry['blend_path'],link=False) as (source,dest):
            if entry['object'] not in source.objects:raise ValueError('Registered mesh object is missing')
            dest.objects=[entry['object']]
        TEMPLATE_OBJECTS[key]=dest.objects[0]
    cached=TEMPLATE_OBJECTS[key]
    obj=cached.copy();obj.data=cached.data.copy()
    return obj


def export_result(job,entry,metrics,info,simulation):
    with tempfile.TemporaryDirectory(prefix='fitme-garment-export-') as temp:
        out=Path(temp)/'model.glb'
        bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',use_selection=True,
            export_yup=True,export_materials='EXPORT',export_texcoords=True,
            export_animations=False,export_skins=False,export_morph=False,
            export_cameras=False,export_lights=False,export_extras=False)
        doc,binary=unpack(out.read_bytes())
    kind=job['recipe']['kind']
    fitting={'kind':kind,'template_id':entry['template_id'],
             'fitting_mode':('sam_body_cloth_collision' if job.get('body_model_id')
                             else 'db_cloth_collision' if simulation else 'catalog_size'),
             'body_model_id':job.get('body_model_id'),
             'simulation_status':simulation['status'] if simulation else None,
             'failure_reasons':simulation['failure_reasons'] if simulation else [],
             'fit_anchor':'fit_anchor_waist' if kind=='slacks' else 'fit_anchor',
             'template_revision':entry.get('revision','1')}
    report={} if job.get('body_model_id') else {
        k:{'target':job['spec'][k], 'measured':float(v), 'abs_error':abs(float(v)-job['spec'][k]),
           'surface':'rest_deformation_cage','unit':'cm'} for k,v in metrics.items()}
    public_job={key:value for key,value in job.items() if key != 'body_glb_b64'}
    doc['scenes'][doc.get('scene',0)]['extras']={**public_job,'unit':'m','fitme_garment':fitting,
        'fitme_garment_measurements':report,'template_geometry':info,'cloth_simulation':simulation}
    return pack(doc,binary)


def main():
    job=json.load(sys.stdin)
    recipe=job['recipe']
    kind,basis=recipe['kind'],recipe['sleeve_basis']
    entry=resolve_template(recipe.get('template_id'),kind)
    if job.get('body_model_id'):
        spec={}
        job={**job,'spec':{},'geometry_mode':'sam_body'}
    elif kind=='slacks':
        if basis!='none':raise ValueError('Slacks require sleeve_basis none')
        spec={}
        job={**job,'spec':{},'geometry_mode':'static'}
    else:
        spec=validate_spec(kind,job['spec'],basis)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for mesh in list(bpy.data.meshes):
        if mesh.users==0:bpy.data.meshes.remove(mesh)
    obj=load_template(entry)
    bpy.context.collection.objects.link(obj)
    stage('template_loaded',vertices=len(obj.data.vertices),polygons=len(obj.data.polygons))
    anchors,metrics,info=body_template(obj,entry) if job.get('body_model_id') else deform(obj,entry,spec,basis)
    stage('sam_template_ready' if job.get('body_model_id') else 'db_deformation_complete')
    stage('garment_geometry',template_id=entry['template_id'],revision=entry.get('revision','1'),
          vertices=len(obj.data.vertices),edges=len(obj.data.edges),polygons=len(obj.data.polygons),
          contact_sample_count=len(obj.data.vertices)+len(obj.data.edges)+len(obj.data.polygons),
          registered_vertices=entry.get('registration',{}).get('vertices'),
          geometry_sha256=info['source_geometry_sha256'],initial_dressing='sam_landmarks_v1')
    simulation = None
    bpy.ops.object.select_all(action='DESELECT')
    root=bpy.data.objects.new('FitMeGarment',None)
    bpy.context.collection.objects.link(root)
    obj.parent=root
    obj.select_set(True);root.select_set(True)
    anchor_objects=[]
    for data in anchors:
        anchor=bpy.data.objects.new(data['name'],None)
        bpy.context.collection.objects.link(anchor);anchor.parent=root
        x,y,z=data['translation']
        anchor.location=(x,-z,y) # glTF axes -> Blender axes
        anchor.select_set(True)
        anchor_objects.append(anchor)
    bpy.context.view_layer.objects.active=obj
    def sync_anchors():
        for data,anchor in zip(anchors,anchor_objects):
            x,y,z=data['translation']; anchor.location=(x,-z,y)
    def checkpoint(positions,report):
        location=os.getenv('FITME_CHECKPOINT')
        if not location:
            return
        clones=[]
        original_names={anchor:anchor.name for anchor in anchor_objects}
        try:
            sync_anchors()
            bpy.ops.object.select_all(action='DESELECT')
            snapshot_root=root.copy(); bpy.context.collection.objects.link(snapshot_root); clones.append(snapshot_root)
            snapshot=obj.copy(); snapshot.data=obj.data.copy(); snapshot.modifiers.clear()
            if snapshot.data.shape_keys: snapshot.shape_key_clear()
            snapshot.parent=snapshot_root; bpy.context.collection.objects.link(snapshot); clones.append(snapshot)
            snapshot.data.vertices.foreach_set('co',[value for point in positions for value in point])
            snapshot.data.update()
            for anchor in anchor_objects:
                original_name=original_names[anchor]
                anchor.name=original_name+'_live'
                marker=anchor.copy(); marker.parent=snapshot_root
                marker.name=original_name
                bpy.context.collection.objects.link(marker); clones.append(marker)
            for item in clones: item.select_set(True)
            bpy.context.view_layer.objects.active=snapshot
            data=export_result(job,entry,metrics,info,report)
            temporary=Path(location+'.tmp'); temporary.write_bytes(data)
            os.replace(temporary,location)
            stage('checkpoint_saved',frame=report.get('frames',0),bytes=len(data))
        finally:
            for item in reversed(clones):
                mesh=item.data if item.type == 'MESH' else None
                bpy.data.objects.remove(item,do_unlink=True)
                if mesh is not None and mesh.users == 0: bpy.data.meshes.remove(mesh)
            bpy.context.view_layer.objects.active=obj
            for anchor,name in original_names.items(): anchor.name=name
    qualities={key:info[key] for key in ('source_mesh_quality','db_mesh_quality','reference_mesh_quality') if key in info}
    invalid_rest=any(not quality['valid'] for quality in qualities.values())
    if invalid_rest:
        simulation={'status':'failed','failure_reasons':['invalid_rest_mesh'],'frames':0,
                    **qualities}
        stage('rest_mesh_validation_failed',**simulation)
        checkpoint([v.co.copy() for v in obj.data.vertices],simulation)
    elif job.get('body_model_id'):
        if not job.get('body_glb_b64'):
            raise ValueError('Missing body collision asset')
        checkpoint([v.co.copy() for v in obj.data.vertices],
                   {'status':'failed','failure_reasons':['simulation_incomplete'],'frames':0})
        simulation=simulate(obj,anchors,kind,job['body_glb_b64'],job['body_model_id'],checkpoint)
    bpy.ops.object.select_all(action='DESELECT')
    sync_anchors()
    for item in [root,obj,*anchor_objects]: item.select_set(True)
    bpy.context.view_layer.objects.active=obj
    data=export_result(job,entry,metrics,info,simulation)
    stage('final_export_complete',bytes=len(data),simulation_status=simulation['status'] if simulation else None)
    with os.fdopen(int(os.environ['FITME_FD']),'wb') as out:out.write(data)

if __name__=='__main__':
    try:main()
    except (ValueError,KeyError) as exc:
        print('FITME_INPUT_ERROR '+str(exc),flush=True)
        raise
