# 역할: 생성된 SAM GLB의 실제 가슴 단면과 판정 여유 수치를 재측정합니다.
"""Blender -b --factory-startup --python-exit-code 3 -P this_file -- --body-glb /tmp/body.glb --chest-width-cm 53

Local diagnostic only. No Blob writes or shape modification.
"""
import argparse
import json
from pathlib import Path
import struct
import sys

import bpy
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from geometry.deform import sections, points, perimeter

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--body-glb',type=Path,required=True)
parser.add_argument('--chest-width-cm',type=float,required=True,help='Actual DB chest flat width for selected size')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
data=args.body_glb.read_bytes()
if data[:4]!=b'glTF': raise ValueError('Expected GLB')
size=struct.unpack_from('<I',data,12)[0]
document=json.loads(data[20:20+size])
extras=document['scenes'][document.get('scene',0)].get('extras',{})
measurements=extras.get('fitme_measurements',{})
chest=measurements.get('chest_girth_cm',{})
height=measurements.get('chest_line_height_cm',{}).get('measured')
if height is None: raise ValueError('GLB has no recorded chest section height')
before=set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(args.body_glb))
vertices=[]; faces=[]
for obj in set(bpy.data.objects)-before:
    if obj.type!='MESH': continue
    offset=len(vertices); obj.data.calc_loop_triangles()
    vertices.extend(tuple(obj.matrix_world @ v.co) for v in obj.data.vertices)
    faces.extend(tuple(offset+i for i in t.vertices) for t in obj.data.loop_triangles)
vertices=np.asarray(vertices); faces=np.asarray(faces,dtype=int)
floor=float(vertices[:,2].min()); body_height=float(np.ptp(vertices[:,2]))
audits=[]
for delta in (-.02,-.01,0.,.01,.02):
    z=floor+height/100+delta*body_height
    contours=[]
    for loop in sections(vertices,faces,np.array([0.,0.,z]),np.array([0.,0.,1.])):
        q=points(vertices,loop)
        contours.append({'girth_cm':float(perimeter(q)*100),'width_cm':float(np.ptp(q[:,0])*100),
                         'depth_cm':float(np.ptp(q[:,1])*100),'center_m':q.mean(0).tolist(),
                         'bounds_m':[q.min(0).tolist(),q.max(0).tolist()]})
    audits.append({'line_height_cm':(z-floor)*100,'height_offset_fraction':delta,'contours':contours})
girth=chest.get('measured')
print('FITME_SAM_CHEST_AUDIT '+json.dumps({'body_geometry_source':extras.get('body_geometry_source'),
    'recorded_chest':chest,'recorded_width':measurements.get('chest_width_cm'),
    'recorded_depth':measurements.get('chest_depth_cm'),
    'actual_height_cm':body_height*100,'chest_width_cm':args.chest_width_cm,
    'computed_ease_cm':2*args.chest_width_cm-girth if girth is not None else None,
    'measurement_diagnostics':extras.get('sam_geometry',{}).get('measurement_diagnostics'),
    'sections':audits},allow_nan=False),flush=True)
