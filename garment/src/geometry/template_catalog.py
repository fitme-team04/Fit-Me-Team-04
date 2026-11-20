# 역할: 템플릿 ID를 모델·바인딩 경로에 연결하고 등록 정보를 검사합니다.
"""Only administrator-registered local template files may be opened."""
import json
import os
from pathlib import Path
import re
from functools import lru_cache

DEFAULT_ROOT = Path(__file__).resolve().parents[2] / 'models' / 'garments'


@lru_cache(maxsize=4)
def registry_at(root):
    return json.loads((Path(root)/'registry.json').read_text(encoding='utf-8'))


def model_root():
    return Path(os.getenv('GARMENT_TEMPLATE_DIR', DEFAULT_ROOT)).resolve()


def safe_path(root, relative):
    if not isinstance(relative,str) or not relative or Path(relative).is_absolute():
        raise ValueError('Template paths must be relative to GARMENT_TEMPLATE_DIR')
    p=(root/relative).resolve()
    if not p.is_relative_to(root) or not p.is_file():
        raise ValueError('Template file is missing or outside the registered directory: '+relative)
    return p


def resolve_template(template_id, kind):
    if not isinstance(template_id,str) or not re.fullmatch(r'[a-z0-9_-]{1,64}',template_id):
        raise ValueError('A valid template_id from category mapping is required')
    root=model_root()
    try:
        registry=registry_at(str(root))
    except (OSError,ValueError) as e:
        raise ValueError('Garment registry unavailable; check models mount') from e
    if registry.get('schema_version')!=1:
        raise ValueError('Unsupported garment registry version')
    entry=registry.get('templates',{}).get(template_id)
    if not entry or entry.get('kind')!=kind:
        raise ValueError('Template is unregistered or has a different garment kind')
    return {**entry,'template_id':template_id,
            'blend_path':str(safe_path(root,entry.get('blend'))),
            'binding_path':str(safe_path(root,entry.get('binding')))}
