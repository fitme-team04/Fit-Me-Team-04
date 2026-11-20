# 역할: 첫 다운로드·검증 캐시 재사용·손상 복구·불일치 및 경로 탈출 차단을 오프라인으로 검사합니다.
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock,patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'garment/src'))
from storage.model_cache import ensure_models


class ModelCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        registry={'templates':{'top':{'kind':'crewneck','blend':'top.blend','binding':'top.npz'},
                              'bottom':{'kind':'slacks','blend':'bottom.blend','binding':'bottom.npz'}}}
        self.payloads={name:name.encode() for name in ('top.blend','top.npz','bottom.blend','bottom.npz')}
        self.payloads['registry.json']=json.dumps(registry).encode()
        self.manifest={'templates':{'crewneck':'top','slacks':'bottom'},'blob_prefix':'releases/test',
                       'files':{k:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for k,v in self.payloads.items()}}
        self.path=root/'manifest.json';self.path.write_text(json.dumps(self.manifest))
        self.env=patch.dict(os.environ,{'GARMENT_MODELS_MANIFEST':str(self.path),'GARMENT_MODEL_CACHE_DIR':str(root/'cache')})
        self.env.start();self.addCleanup(self.env.stop)
        self.transfers=[];self.corrupt=False
        owner=self
        class Blob:
            def __init__(self,name):self.name=name
            def get_blob_properties(self):return type('Properties',(),{'size':len(owner.payloads[self.name]),'etag':'pinned'})()
            def download_blob(self,**kwargs):
                owner.assertEqual(kwargs['etag'],'pinned')
                owner.transfers.append(self.name)
                payload=owner.payloads[self.name]
                if owner.corrupt:payload=b'x'*len(payload)
                return type('Download',(),{'readinto':lambda _,stream:stream.write(payload)})()
        self.service=MagicMock()
        self.service.__enter__.return_value=self.service
        self.service.get_container_client.return_value.get_blob_client.side_effect=lambda name:Blob(name.split('/')[-1])

    def patches(self):
        return patch('azure.storage.blob.BlobServiceClient',return_value=self.service),patch('azure.identity.DefaultAzureCredential')

    def test_first_download_then_offline_reuse_and_repair(self):
        service,credential=self.patches()
        with service as client,credential:
            root=ensure_models()
            self.assertEqual(len(self.transfers),5)
            self.assertEqual(ensure_models(),root)
            self.assertEqual(client.call_count,1)
            (root/'top.npz').write_bytes(b'broken')
            ensure_models()
            self.assertEqual(len(self.transfers),6)
            self.assertEqual((root/'top.npz').read_bytes(),self.payloads['top.npz'])

    def test_hash_mismatch_stops_startup_and_removes_temporary(self):
        self.corrupt=True
        service,credential=self.patches()
        with service,credential,self.assertRaises(ValueError):ensure_models()
        self.assertFalse(any(p.name=='registry.json' for p in Path(self.temp.name).rglob('*')))

    def test_container_root_has_no_leading_slash(self):
        self.manifest['blob_prefix']=''
        self.path.write_text(json.dumps(self.manifest))
        service,credential=self.patches()
        with service,credential:
            ensure_models()
        actual=[call.args[0] for call in self.service.get_container_client.return_value.get_blob_client.call_args_list]
        self.assertEqual(set(actual),set(self.payloads))
        self.assertTrue(all('/' not in name for name in actual))

    def test_manifest_path_traversal_rejected_before_network(self):
        self.manifest['files']['../escape']={'bytes':1,'sha256':'0'*64}
        self.path.write_text(json.dumps(self.manifest))
        with self.assertRaises(ValueError):ensure_models()


if __name__=='__main__':unittest.main()
