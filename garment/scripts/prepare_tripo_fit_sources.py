# 역할: Tripo 원본을 보존하고 좌표 방향·단위를 맞춘 경량 의류 사본을 생성합니다.
import argparse
import json
from pathlib import Path
import sys
import bpy
import numpy as np
from mathutils import Matrix


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True,type=Path)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);root=args.root.resolve()
    for kind in ('shirt','pants'):
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        source=next((root/('source-'+kind)).rglob('model.glb'))
        bpy.ops.import_scene.gltf(filepath=str(source),merge_vertices=True)
        obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
        bpy.context.view_layer.update()
        transform=Matrix(((0,1,0,0),(-1,0,0,0),(0,0,1,.5),(0,0,0,1)))
        obj.data.transform(transform@obj.matrix_world);obj.parent=None;obj.matrix_world=Matrix.Identity(4)
        obj.data.calc_loop_triangles();original_faces=len(obj.data.loop_triangles)
        bpy.context.view_layer.objects.active=obj
        modifier=obj.modifiers.new('FitMeWorkingCopy','DECIMATE');modifier.ratio=min(1.,24000/original_faces)
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        obj.data.calc_loop_triangles()
        vertices=np.array([v.co[:] for v in obj.data.vertices])
        report={'source_triangles':original_faces,'working_triangles':len(obj.data.loop_triangles),
                'vertices':len(vertices),'min':vertices.min(0).tolist(),'max':vertices.max(0).tolist(),
                'source_unchanged':True,'uv_layers':len(obj.data.uv_layers),'materials':len(obj.data.materials)}
        (root/(kind+'-working-report.json')).write_text(json.dumps(report,indent=2)+'\n')
        bpy.ops.export_scene.gltf(filepath=str(root/(kind+'-working.glb')),export_format='GLB',use_selection=False)
        print('FITME_SOURCE '+kind+' '+json.dumps(report),flush=True)


if __name__=='__main__':main()
