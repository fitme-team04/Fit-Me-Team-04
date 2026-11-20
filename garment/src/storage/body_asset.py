# 역할: 요청 소유자의 충돌용 신체 GLB를 읽고 크기와 해시를 검증합니다.
"""Fetch only the requesting owner's immutable avatar; no caller-provided URL."""
from hashlib import sha256
import os
import re

from core.cloth_contract import MAX_BODY_BYTES


def body_path(subject, model_id):
    if not isinstance(model_id, str) or not re.fullmatch(r'[a-f0-9]{64}', model_id):
        raise ValueError('Invalid body model ID')
    return f'v2/avatars/{sha256(subject.encode()).hexdigest()}/{model_id}/model.glb'


def load_body(subject, model_id):
    from storage.blob_assets import storage
    from azure.core.exceptions import AzureError
    from fastapi import HTTPException
    service, _ = storage()
    blob = service.get_blob_client(container=os.getenv('BODY_STORAGE_CONTAINER', 'body-glb'),
                                   blob=body_path(subject, model_id))
    try:
        size = blob.get_blob_properties().size
        if not 20 <= size <= MAX_BODY_BYTES:
            raise ValueError('Body GLB size out of range')
        data = blob.download_blob(offset=0, length=size, max_concurrency=1).readall()
    except AzureError as exc:
        raise HTTPException(503, 'Body collision asset unavailable') from exc
    if len(data) != size or sha256(data).hexdigest() != model_id or data[:4] != b'glTF':
        raise ValueError('Body collision asset does not match model ID')
    return data
