# 역할: MHR 기준 포즈와 FitMe 제어 메시의 바인딩을 생성합니다.
"""Run in Blender with the supplied control .blend; bind in its fixed A pose."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils.bvhtree import BVHTree
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from geometry.bind_sam import digest
from core.contract import FIXED_POSE
from geometry.deform import solve
from geometry.glb import export


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pose', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args(sys.argv[sys.argv.index('--')+1:])
    obj = bpy.data.objects['GEO-body_male_realistic']
    obj.data.calc_loop_triangles()
    base = np.array([v.co[:] for v in obj.data.shape_keys.reference_key.data])
    control, tri, _, _, _, _ = solve('male', {'male':FIXED_POSE})
    with np.load(args.pose, allow_pickle=False) as z:
        neutral, faces = z['vertices'], z['faces']
        skeleton, joint_names = z['skeleton'], z['joint_names'].tolist()
        calibration_id, mhr_hash = str(z['calibration_id']), str(z['mhr_sha256'])
    # MHR: X right, Y up, Z front; Blender control: X right, Z up, -Y front.
    rotation = np.array([[1.,0,0],[0,0,1],[0,-1,0]])
    scale = np.ptp(control[:,2])/np.ptp(neutral[:,1])
    linear = rotation*scale
    vertices = neutral @ linear
    shoulders = skeleton[[joint_names.index('l_uparm'), joint_names.index('r_uparm')],:3] @ linear
    translation = np.array([-vertices[:,0].mean(), -shoulders[:,1].mean(),
                             control[:,2].min()-vertices[:,2].min()])
    vertices += translation
    tree = BVHTree.FromPolygons(control.tolist(), tri.tolist(), all_triangles=True)
    ids, weights, distances = [], [], []
    for vertex in vertices:
        hit, _, index, distance = tree.find_nearest(vertex)
        a,b,c = control[tri[index]]
        uv = np.linalg.lstsq(np.column_stack([b-a,c-a]),np.asarray(hit)-a,rcond=None)[0]
        weights.append([1-uv.sum(), *uv]); ids.append(tri[index]); distances.append(distance)
    weights = np.asarray(weights)
    if not np.isfinite(weights).all() or not np.allclose(weights.sum(1),1) or weights.min() < -.001:
        raise ValueError('Invalid barycentric weights')
    if np.percentile(distances,95) > .08 or max(distances) > .20:
        raise ValueError('Alignment exceeds 8 cm p95 / 20 cm maximum; inspect meshes')
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(output, vertices=vertices, faces=faces, neutral=neutral,
        sam_faces=faces, linear=linear, translation=translation, ids=np.asarray(ids,dtype=np.int32),
        weights=weights, ref_hash=digest(base,tri), control_reference=control,
        schema_version=np.array(2), calibration_id=np.array(calibration_id),mhr_sha256=np.array(mhr_hash),
        fixed_pose_json=np.array(json.dumps(FIXED_POSE,sort_keys=True)))
    report={'control_vertices':len(base),'control_triangles':len(tri),
        'mhr_vertices':len(vertices),'mhr_triangles':len(faces),'control_ref_hash':digest(base,tri),
        'surface_distance_cm':{'median':100*float(np.median(distances)),
          'p95':100*float(np.percentile(distances,95)), 'max':100*float(max(distances))},
        'scale':float(scale),'calibration_id':calibration_id,
        'fixed_pose':FIXED_POSE,'binding_reference':'posed control, not raw Basis',
        'accuracy_note':'Nearest-surface correspondence; this is not anthropometric validation.'}
    output.with_suffix('.report.json').write_text(json.dumps(report,indent=2))
    output.with_suffix('.preview.glb').write_bytes(export([('MHR_reference',vertices,faces)],[]))
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    main()
