# 역할: MHR 모델에서 기준 A 포즈 데이터를 생성합니다.
"""Create a reproducible 45 degree MHR reference without a photo or SAM weights."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import torch
from scipy.optimize import least_squares
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from storage.asset_files import require_model_file


def sha256(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mhr', default='/models/mhr_model.pt')
    ap.add_argument('--output', default='/models/a_pose.npz')
    args = ap.parse_args()
    require_model_file(args.mhr)
    torch.set_num_threads(1)
    rig = torch.jit.load(args.mhr, map_location='cpu').eval()
    names = list(rig.get_parameter_names())[:204]
    joints = list(rig.get_joint_names())
    if names[130:136] != ['spine_length_flexible', 'neck_length_flexible',
                         'shoulder_width_flexible', 'arm_length_flexible',
                         'hip_width_flexible', 'leg_length_flexible']:
        raise ValueError('Unsupported MHR parameter layout')
    params = np.zeros(204, np.float32)
    angles = {}
    for side, sign in [('l', 1), ('r', -1)]:
        indices = [names.index(side+'_'+n) for n in
                   ['uparm_twist', 'uparm_ry', 'uparm_rz', 'elbow_bend']]
        shoulder, elbow, wrist = [joints.index(side+'_'+n) for n in
                                  ['uparm', 'lowarm', 'wrist']]
        direction = np.array([sign, -1., .16])
        direction /= np.linalg.norm(direction)
        def skeleton(x):
            candidate = params.copy()
            candidate[indices] = x
            # The character also has 45 identity slots, unlike rig.forward.
            packed = np.r_[candidate, np.zeros(45, np.float32)]
            with torch.inference_mode():
                jp = rig.character_torch.model_parameters_to_joint_parameters(
                    torch.from_numpy(packed[None]))
                return rig.character_torch.joint_parameters_to_skeleton_state(jp)[0,:,:3].numpy()
        def residual(x):
            skel = skeleton(x)
            upper = skel[elbow]-skel[shoulder]
            lower = skel[wrist]-skel[elbow]
            return np.r_[upper/np.linalg.norm(upper)-direction,
                         lower/np.linalg.norm(lower)-direction, .005*x[0]]
        fit = least_squares(residual, [.02]*4, diff_step=.002, max_nfev=150,
                            xtol=1e-7, gtol=1e-7, ftol=1e-7)
        params[indices] = fit.x
        skel = skeleton(fit.x)
        delta = skel[wrist]-skel[shoulder]
        angles[side] = float(np.degrees(np.arctan2(abs(delta[0]), -delta[1])))
        if abs(angles[side]-45) > 1 or np.linalg.norm(residual(fit.x)) > .03:
            raise ValueError('A pose calibration failed')
    with torch.inference_mode():
        verts, skel = rig(torch.zeros(1,45), torch.from_numpy(params[None]), torch.zeros(1,72))
    verts = verts[0].numpy()/100
    faces = rig.character_torch.mesh.faces.numpy().astype(np.int32)
    if verts.shape != (18439,3) or faces.shape != (36874,3):
        raise ValueError('Unexpected MHR LOD1 topology')
    model_hash = sha256(args.mhr)
    calibration_id = hashlib.sha256(verts.astype('<f4').tobytes()+
        faces.astype('<i4').tobytes()+params.astype('<f4').tobytes()+model_hash.encode()).hexdigest()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, vertices=verts, faces=faces, pose=params[None,:130],
        pose_indices=np.arange(130,dtype=np.int32), model_parameters=params[None],
        parameter_names=np.array(names), skeleton=skel[0].numpy()/np.array([100,100,100,1,1,1,1,1]),
        joint_names=np.array(joints), schema_version=np.array(2),
        mhr_sha256=np.array(model_hash), calibration_id=np.array(calibration_id))
    output.with_suffix('.report.json').write_text(json.dumps({
        'source':'facebookresearch/MHR v1.0.1', 'photo_used':False,
        'vertices':len(verts), 'faces':len(faces), 'arm_angles_deg':angles,
        'pose_indices':'0:130', 'preserved_personal_size_indices':'130:204',
        'mhr_sha256':model_hash, 'calibration_id':calibration_id}, indent=2))
    print('PASS: canonical MHR A pose', angles)

if __name__ == '__main__':
    main()
