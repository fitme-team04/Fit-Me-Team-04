# 역할: 승인된 계정으로 SAM·검출기·시야각 추정 모델을 준비합니다.
"""Run once with HF_TOKEN from an approved Hugging Face account; keep tokens out of files."""
import argparse,hashlib,json,os,sys,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from storage.asset_files import require_model_file
from download_blob_models import file_sha256
os.environ['HF_HUB_OFFLINE']='0'
from huggingface_hub import snapshot_download,hf_hub_download
SAM_REVISION='11aaa346c7204874a1cbafe3d39a979080b2c55a'
MOGE_REVISION='cb0e8bbd6b1e243589717c78e750b1ba4c093acf'
VITDET_URL='https://dl.fbaipublicfiles.com/detectron2/ViTDet/COCO/cascade_mask_rcnn_vitdet_h/f328730692/model_final_f05665.pkl'

def sha256(path):
    return file_sha256(path)

def download(url,target):
    if target.is_file() and target.stat().st_size>1024:
        print('Exists:',target.name);return
    target.parent.mkdir(parents=True,exist_ok=True)
    part=target.with_suffix(target.suffix+'.part')
    try:
        with urllib.request.urlopen(url,timeout=120) as src,part.open('wb') as dst:
            while chunk:=src.read(8*1024*1024):dst.write(chunk)
        if part.stat().st_size<1024:raise ValueError('Incomplete model download')
        part.replace(target)
    finally:part.unlink(missing_ok=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--models',default='/models');args=ap.parse_args()
    root=Path(args.models);root.mkdir(parents=True,exist_ok=True)
    require_model_file(root/'mhr_model.pt')
    token=os.environ.get('HF_TOKEN')
    if not token:raise SystemExit('Set HF_TOKEN from an account with SAM 3D Body access. Do not put it in Git.')
    try:
        snapshot_download('facebook/sam-3d-body-dinov3',revision=SAM_REVISION,
            allow_patterns=['model.ckpt','model_config.yaml','LICENSE','README.md'],
            local_dir=root/'sam',token=token)
    except Exception as exc:
        raise SystemExit('SAM download failed. Confirm account approval/token read access and network. '
                         'No access restriction is bypassed. Error type: '+type(exc).__name__) from None
    download(VITDET_URL,root/'vitdet/model_final_f05665.pkl')
    hf_hub_download('Ruicheng/moge-2-vitl-normal','model.pt',revision=MOGE_REVISION,
                    local_dir=root/'moge',token=token)
    paths=['sam/model.ckpt','sam/model_config.yaml','vitdet/model_final_f05665.pkl',
           'moge/model.pt','mhr_model.pt','a_pose.npz','sam_body.npz','fitme_depth_fixed.blend']
    records={p:{'bytes':(root/p).stat().st_size,'sha256':sha256(root/p)} for p in paths}
    (root/'download_manifest.json').write_text(json.dumps({'sam_revision':SAM_REVISION,
        'moge_revision':MOGE_REVISION,'files':records},indent=2))
    # UID 10001 only needs read permission during normal operation.
    for parent,dirs,files in os.walk(root):
        Path(parent).chmod(0o755)
        for name in files:(Path(parent)/name).chmod(0o644)
    print('PASS: model files downloaded. Next run sam_reference.py check with HF_HUB_OFFLINE=1.')

if __name__=='__main__':main()
