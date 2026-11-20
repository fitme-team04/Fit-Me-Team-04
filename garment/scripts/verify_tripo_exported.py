# 역할: 실제 내보낸 Tripo 착장 GLB를 새 Blender 프로세스에서 재수입해 신체 관통과 UV·내장 질감을 검증합니다.
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import bpy
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from geometry.glb import unpack
from geometry.body_clearance import require_clear
from rebuild_cc0_reference import inspect,vertices_world,triangles


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--file',type=Path)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);root=args.root.resolve()
    if args.file is None:
        for file in sorted((root/'validation').glob('*/*.glb')):
            subprocess.run([bpy.app.binary_path,'-b','-Y','--factory-startup','--python-exit-code','1','-P',str(Path(__file__).resolve()),
                '--','--root',str(root),'--file',str(file)],check=True)
        return
    file=args.file.resolve();name=file.parent.name
    body_name='joint_'+str(.95 if name.endswith('0.9') else 1.05) if name.startswith('garment_joint') else name
    with np.load(root/'bodies'/(body_name+'.npz')) as b:body,body_faces=b['vertices'],b['faces']
    blob=file.read_bytes();doc,_=unpack(blob)
    assert all('bufferView' in image for image in doc['images'])
    assert all('TEXCOORD_0' in p['attributes'] for m in doc['meshes'] for p in m['primitives'])
    bpy.ops.import_scene.gltf(filepath=str(file))
    obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    check=inspect(vertices_world(obj),triangles(obj),body,body_faces);require_clear(check)
    report_path=root/'validation/export-validation.json'
    report=json.loads(report_path.read_text()) if report_path.exists() else {}
    report[str(file.relative_to(root))]={'check':check,'sha256':hashlib.sha256(blob).hexdigest(),'embedded_textures':True,'uv':True}
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: exported '+name+'/'+file.name,flush=True)


if __name__=='__main__':main()
