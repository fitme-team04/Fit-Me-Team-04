# 역할: Blob의 네 신체 원본을 내려받고 크기·SHA-256 검증 후 캐시를 교체합니다.
"""Download pinned model assets from private Azure Blob storage before API startup."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

MODEL_FILES = ('mhr_model.pt', 'fitme_depth_fixed.blend', 'a_pose.npz', 'sam_body.npz')


def file_sha256(path):
    # VM 호스트의 Python 3.10에서도 실행되도록 file_digest(3.11+) 대신 스트리밍합니다.
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def selected_models(records):
    """Require the complete compatible set; keep additional manifest records local."""
    missing = set(MODEL_FILES) - records.keys()
    if missing:
        raise ValueError('Model manifest is incomplete: ' + ', '.join(sorted(missing)))
    return MODEL_FILES


def valid_file(path, metadata):
    if not path.is_file() or path.stat().st_size != metadata['bytes']:
        return False
    return file_sha256(path) == metadata['sha256']


def download_one(container, name, target, metadata):
    if valid_file(target, metadata):
        print('VERIFIED:', name)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.model-', delete=False) as stream:
            temporary = Path(stream.name)
            blob = container.get_blob_client(name)
            properties = blob.get_blob_properties()
            if properties.size != metadata['bytes']:
                raise ValueError('Unexpected Blob size: ' + name)
            # Pin this download to the version inspected above.
            from azure.core import MatchConditions
            blob.download_blob(etag=properties.etag,
                               match_condition=MatchConditions.IfNotModified).readinto(stream)
        if not valid_file(temporary, metadata):
            raise ValueError('Model size/SHA-256 mismatch: ' + name)
        temporary.chmod(0o644)
        temporary.replace(target)
        print('DOWNLOADED AND VERIFIED:', name)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', help='Optional private dotenv file; existing environment wins')
    parser.add_argument('--models', default=str(Path(__file__).resolve().parents[1] / 'models'))
    parser.add_argument('--all', action='store_true', help='Compatibility option; all four models are always downloaded')
    args = parser.parse_args()
    if args.env_file:
        from dotenv import load_dotenv
        if not Path(args.env_file).is_file():
            parser.error('Environment file does not exist')
        load_dotenv(args.env_file, override=False)
    root = Path(args.models).resolve()
    manifest = Path(__file__).resolve().parents[1] / 'models' / 'bundled_assets.json'
    # Containers mount /models rather than packaging model files into the image.
    if not manifest.is_file():
        manifest = root / 'bundled_assets.json'
    records = json.loads(manifest.read_text(encoding='utf-8'))['files']
    selected = selected_models(records)
    # An offline VM with verified assets does not need Azure credentials.
    if all(valid_file(root / name, records[name]) for name in selected):
        print('PASS: selected local models already verified')
        return
    from azure.storage.blob import BlobServiceClient
    from azure.identity import DefaultAzureCredential
    from contextlib import ExitStack
    with ExitStack() as stack:
        connection = os.getenv('AZURE_MODELS_CONNECTION_STRING', '').strip()
        if connection:
            service = stack.enter_context(BlobServiceClient.from_connection_string(connection))
        else:
            url = os.getenv('AZURE_MODELS_ACCOUNT_URL', 'https://fitmemlstdev.blob.core.windows.net')
            if not url.startswith('https://') or '?' in url:
                raise ValueError('Use an HTTPS account URL without a SAS query')
            secret = os.getenv('AZURE_MODELS_SAS_TOKEN', '').strip().lstrip('?')
            credential = secret or stack.enter_context(DefaultAzureCredential())
            service = stack.enter_context(BlobServiceClient(url, credential=credential))
        container = service.get_container_client(os.getenv('AZURE_MODELS_CONTAINER', 'avatar-models'))
        for name in selected:
            download_one(container, name, root / name, records[name])


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Azure exceptions may contain a signed URL. Never print them or credentials.
        raise SystemExit('Model download failed (' + type(exc).__name__ +
                         '). Check authentication, Blob names, network and pinned hashes.') from None
