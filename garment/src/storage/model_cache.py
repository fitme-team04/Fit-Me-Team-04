# 역할: 서버 시작 시 고정된 Blob 모델 묶음을 검증·다운로드하고 요청에서 재사용할 로컬 경로를 설정합니다.
import hashlib
import json
import os
from pathlib import Path
import tempfile
from contextlib import ExitStack


def manifest_path():
    return Path(os.getenv('GARMENT_MODELS_MANIFEST',str(Path(__file__).resolve().parents[2]/'models/bundled_garments.json')))


def valid(path,record):
    if not path.is_file() or path.stat().st_size!=record['bytes']:return False
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()==record['sha256']


def ensure_models():
    manifest=json.loads(manifest_path().read_text(encoding='utf-8'))
    files=manifest['files']
    if 'registry.json' not in files:raise ValueError('Model manifest lacks registry')
    if any(Path(name).name!=name or '/' in name or '\\' in name or ':' in name or name in ('.','..') for name in files):
        raise ValueError('Invalid model manifest path')
    key=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()[:20]
    root=Path(os.getenv('GARMENT_MODEL_CACHE_DIR','/models/cache'))/key
    root.mkdir(parents=True,exist_ok=True)
    missing=[name for name in files if not valid(root/name,files[name])]
    if missing:
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient
        from azure.core import MatchConditions
        with ExitStack() as stack:
            credential=stack.enter_context(DefaultAzureCredential())
            service=stack.enter_context(BlobServiceClient(
                os.getenv('GARMENT_MODELS_ACCOUNT_URL','https://fitmemlstdev.blob.core.windows.net'),credential=credential))
            container=service.get_container_client(os.getenv('GARMENT_MODELS_CONTAINER','garment-models'))
            for name in sorted(missing,key=lambda n:n=='registry.json'):
                prefix=manifest.get('blob_prefix','').strip('/')
                blob=container.get_blob_client(prefix+'/'+name if prefix else name)
                props=blob.get_blob_properties()
                if props.size!=files[name]['bytes']:raise ValueError('Model Blob size mismatch')
                temporary=None
                try:
                    with tempfile.NamedTemporaryFile(dir=root,delete=False) as output:
                        temporary=Path(output.name)
                        blob.download_blob(etag=props.etag,match_condition=MatchConditions.IfNotModified).readinto(output)
                    if not valid(temporary,files[name]):raise ValueError('Model Blob hash mismatch')
                    temporary.chmod(0o644);temporary.replace(root/name)
                finally:
                    if temporary is not None:temporary.unlink(missing_ok=True)
    registry=json.loads((root/'registry.json').read_text())
    if set(registry['templates'])!=set(manifest['templates'].values()):
        raise ValueError('Unexpected template registry entries')
    for kind,tid in manifest['templates'].items():
        entry=registry['templates'][tid]
        if entry['kind']!=kind:raise ValueError('Model kind mismatch')
        for field in ('blend','binding'):
            if entry[field] not in files:raise ValueError('Unpinned template file')
    os.environ['GARMENT_TEMPLATE_DIR']=str(root.resolve())
    return root
