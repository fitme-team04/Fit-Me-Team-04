# 역할: 로컬 모델의 누락·빈 파일·잘못된 LFS 포인터를 검사합니다.
"""Check that a local model contains actual bytes before loading or hashing it."""
from pathlib import Path


def require_model_file(path):
    """Return a local model path, rejecting a missing file or an LFS pointer."""
    model = Path(path)
    recovery = (
        "On the VM host, run 'python scripts/download_blob_models.py "
        "--env-file .env.models' from avatar, then rerun the asset check."
    )
    if not model.is_file():
        raise FileNotFoundError(f"Model file is missing: {model}. {recovery}")
    with model.open('rb') as stream:
        header = stream.read(128)
    if header.startswith(b'version https://git-lfs.github.com/spec/v1'):
        raise ValueError(f"GIT_LFS_POINTER: {model} is an LFS pointer, not model bytes. {recovery}")
    if not header:
        raise ValueError(f"Model file is empty: {model}. {recovery}")
    return model
