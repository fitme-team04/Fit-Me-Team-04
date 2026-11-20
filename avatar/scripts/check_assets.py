# 역할: 모델 파일과 포즈·바인딩의 해시·위상 호환성을 검사합니다.
"""Check local prerequisites without calling Azure or running photograph inference."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from storage.asset_files import require_model_file

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--models',default='/models')
    ap.add_argument('--with-checkpoints',action='store_true');args=ap.parse_args()
    root=Path(args.models)
    try:require_model_file(root/'mhr_model.pt')
    except (ValueError,FileNotFoundError) as exc:raise SystemExit(str(exc)) from None
    files=['fitme_depth_fixed.blend','mhr_model.pt','a_pose.npz','sam_body.npz']
    if args.with_checkpoints:files+=['sam/model.ckpt','sam/model_config.yaml','vitdet/model_final_f05665.pkl','moge/model.pt']
    missing=[p for p in files if not (root/p).is_file()]
    if missing:raise SystemExit('MISSING: '+', '.join(missing))
    with np.load(root/'a_pose.npz',allow_pickle=False) as pose, np.load(root/'sam_body.npz',allow_pickle=False) as binding:
        assert int(pose['schema_version'])==int(binding['schema_version'])==2
        assert str(pose['calibration_id'])==str(binding['calibration_id'])
        assert np.array_equal(pose['faces'],binding['sam_faces'])
        assert np.allclose(pose['vertices'],binding['neutral'])
        assert np.allclose(binding['weights'].sum(1),1)
        assert binding['ids'].min()>=0 and binding['ids'].max()<len(binding['control_reference'])
        assert np.array_equal(pose['pose_indices'],np.arange(130))
        with (root/'mhr_model.pt').open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
        assert actual==str(pose['mhr_sha256'])==str(binding['mhr_sha256'])
    manifest=root/'bundled_assets.json'
    if manifest.exists():
        for name,meta in json.loads(manifest.read_text())['files'].items():
            with (root/name).open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
            assert actual==meta['sha256'],name+' changed; regenerate assets/manifest together'
    print('PASS: files, MHR hash, topology, pose and binding weights')

if __name__=='__main__':main()
