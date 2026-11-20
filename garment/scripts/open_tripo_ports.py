# 역할: Tripo 의류의 막힌 목·허리 내부와 밑단을 착장 가능한 통로로 열고 원본은 보존합니다.
import argparse
import json
from pathlib import Path
import sys
import bpy
import bmesh
import numpy as np


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True,type=Path)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);root=args.root.resolve()
    for kind in ('shirt','pants'):
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        bpy.ops.import_scene.gltf(filepath=str(root/(kind+'-working.glb')),merge_vertices=True)
        obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
        bm=bmesh.new();bm.from_mesh(obj.data)
        if kind=='pants':
            bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,
                plane_co=(0,0,.065),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
        else:
            torso=[f for f in bm.faces if all(abs(v.co.x)<.32 for v in f.verts)]
            bmesh.ops.bisect_plane(bm,geom=list(set(v for f in torso for v in f.verts))+list(set(e for f in torso for e in f.edges))+torso,
                dist=1e-6,plane_co=(0,0,.155),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
            sleeves=[f for f in bm.faces if all(abs(v.co.x)>.30 for v in f.verts)]
            bmesh.ops.bisect_plane(bm,geom=list(set(v for f in sleeves for v in f.verts))+list(set(e for f in sleeves for e in f.edges))+sleeves,
                dist=1e-6,plane_co=(0,0,.155),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
        remove=[]
        for face in bm.faces:
            p=face.calc_center_median()
            inside=((p.x/.125)**2+(p.y/.105)**2<1 and p.z>.72) if kind=='shirt' else ((p.x/.166)**2+(p.y/.128)**2<1 and p.z>.85)
            if inside:remove.append(face)
        removed=len(remove)
        bmesh.ops.delete(bm,geom=remove,context='FACES')
        loose=[v for v in bm.verts if not v.link_faces]
        if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        bm.to_mesh(obj.data);bm.free();obj.data.update()
        bpy.ops.export_scene.gltf(filepath=str(root/(kind+'-open.glb')),export_format='GLB')
        print('FITME_PORTS '+json.dumps({'kind':kind,'interior_faces_removed':removed}),flush=True)


if __name__=='__main__':main()
