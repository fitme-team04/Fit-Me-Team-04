# 역할: 사진에서 한 사람의 신체 메시를 SAM으로 복원합니다.
"""Run in the GPU Python environment. infer preserves identity and locks pose."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import cv2
import numpy as np
import torch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from storage.asset_files import require_model_file
from core.photo_visibility import PhotoFramingError, validate_full_body


def make_estimator():
    # Explicit local files: no implicit notebook, detector or FOV cache download.
    from sam_3d_body import load_sam_3d_body, SAM3DBodyEstimator
    from tools.build_detector import HumanDetector
    if not torch.cuda.is_available():
        raise RuntimeError('SAM requires a CUDA GPU in this deployment')
    checkpoint = os.getenv('SAM_CHECKPOINT','/models/sam/model.ckpt')
    mhr_path = os.environ['SAM_MHR']
    model, cfg = load_sam_3d_body(checkpoint, device='cuda', mhr_path=mhr_path)
    # T4 does not support bfloat16; use fp16 if the downloaded config selected bf16.
    if getattr(model,'backbone_dtype',None) == torch.bfloat16 and not torch.cuda.is_bf16_supported():
        model.cfg.defrost()
        model.cfg.TRAIN.FP16_TYPE = 'float16'
        model.cfg.freeze()
        model.backbone_dtype = model.convert_to_fp16()
    detector = HumanDetector(name='vitdet', device='cuda',
        path=os.getenv('SAM_DETECTOR_DIR','/models/vitdet'))
    fov = None
    if os.getenv('SAM_FOV','moge2') == 'moge2':
        from tools.build_fov_estimator import FOVEstimator
        fov = FOVEstimator(name='moge2', device='cuda',
            path=os.getenv('SAM_FOV_CHECKPOINT','/models/moge/model.pt'))
    estimator = SAM3DBodyEstimator(sam_3d_body_model=model,model_cfg=cfg,
        human_detector=detector,human_segmentor=None,fov_estimator=fov)
    return estimator


class InputError(ValueError):
    def __init__(self, message, *, code='single_person_required'):
        super().__init__(message)
        self.code=code


def load_state():
    require_model_file(os.environ['SAM_MHR'])
    with np.load(os.environ['SAM_POSE'],allow_pickle=False) as z:
        if int(z['schema_version'])!=2: raise ValueError('Regenerate A pose with prepare_pose.py')
        pose=z['pose'];indices=z['pose_indices'];faces=z['faces'];neutral=z['vertices']
        model_hash=str(z['mhr_sha256']);calibration_id=str(z['calibration_id'])
    with open(os.environ['SAM_MHR'],'rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=model_hash:
            raise ValueError('MHR file changed. Rebuild pose and binding together.')
    estimator=make_estimator()
    # Use the very same rig loaded into SAM instead of loading a second copy on GPU.
    rig=estimator.model.head_pose.mhr
    rig_faces=rig.character_torch.mesh.faces.detach().cpu().numpy()
    if not np.array_equal(rig_faces,faces) or not np.array_equal(np.asarray(estimator.faces),faces):
        raise ValueError('SAM checkpoint and prepared MHR topology differ')
    canonical=torch.zeros((1,204),device='cuda')
    canonical[:,indices]=torch.from_numpy(pose).to('cuda')
    with torch.inference_mode():
        check,_=rig(torch.zeros((1,45),device='cuda'),canonical,torch.zeros((1,72),device='cuda'))
    if not np.allclose(check[0].cpu().numpy()/100,neutral,atol=2e-5,rtol=1e-5):
        raise ValueError('MHR reference geometry differs from calibration')
    return estimator, rig, pose, indices, faces, calibration_id


def infer_photo(state, photo_path, output_path):
    estimator, rig, pose, indices, faces, calibration_id = state
    photo=cv2.imread(photo_path)
    if photo is None: raise ValueError('Unreadable photo')
    with torch.inference_mode():
        people=estimator.process_one_image(cv2.cvtColor(photo,cv2.COLOR_BGR2RGB))
    if len(people)!=1:
        raise InputError('Expected exactly one person')
    person=people[0]
    # Check photo-space framing before the output pose is replaced with A pose.
    try:
        photo_validation=validate_full_body(person,photo.shape)
    except PhotoFramingError as exc:
        print('FITME_PHOTO_REJECTED '+exc.reason,flush=True)
        raise InputError('Expected a full-body photo',code='full_body_required') from exc
    params=np.asarray(person['mhr_model_params'],dtype=np.float32).reshape(1,204).copy()
    shape=np.asarray(person['shape_params'],dtype=np.float32).reshape(1,45)
    # 0:130 is pose, 130:136 flexible lengths, 136:204 scales.
    params[:,indices]=pose
    with torch.inference_mode():
        vertices,_=rig(torch.from_numpy(shape).to('cuda'),torch.from_numpy(params).to('cuda'),
                       torch.zeros((1,72),device='cuda'))
    vertices=vertices[0].cpu().numpy()/100
    if not np.isfinite(vertices).all(): raise ValueError('Invalid MHR mesh')
    np.savez_compressed(output_path,vertices=vertices,faces=faces,
                        calibration_id=np.array(calibration_id),
                        photo_validation_json=np.array(json.dumps(photo_validation)))

def main():
    import json
    parser=argparse.ArgumentParser()
    parser.add_argument('mode', choices=['infer','check','serve'])
    parser.add_argument('photo', nargs='?')
    parser.add_argument('output', nargs='?')
    args=parser.parse_args()
    if args.mode == 'infer' and (not args.photo or not args.output):
        parser.error('infer requires photo and output')
    try:
        state=load_state()
    except Exception as exc:
        print('FITME_SAM_FAILURE '+type(exc).__name__, flush=True)
        raise
    if args.mode == 'check':
        print('PASS: GPU model, detector, FOV, MHR and calibration loaded offline', flush=True)
        return
    if args.mode == 'infer':
        try:
            infer_photo(state,args.photo,args.output)
        except InputError as exc:
            print('FITME_INPUT_ERROR '+exc.code, flush=True)
            raise SystemExit(2)
        return
    print('FITME_SAM_REPLY '+json.dumps({'status':'ready'}), flush=True)
    for line in sys.stdin:
        try:
            job=json.loads(line)
            infer_photo(state,job['photo'],job['output'])
            result={'status':'ok'}
        except InputError as exc:
            result={'status':'input_error','code':exc.code}
        except Exception as exc:
            # Only the exception class is logged; request paths and data are excluded.
            print('FITME_SAM_FAILURE '+type(exc).__name__, flush=True)
            raise SystemExit(1)
        print('FITME_SAM_REPLY '+json.dumps(result), flush=True)


if __name__=='__main__':
    main()
