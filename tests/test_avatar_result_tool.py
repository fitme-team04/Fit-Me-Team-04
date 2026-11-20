# 역할: 실제 결과 검증 도구가 GLB·메타데이터 불일치를 실패로 보고하고 서명 URL을 남기지 않는지 검사합니다.
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'avatar/src'))
from geometry.mesh_anchors import extract


class ResultToolTests(unittest.TestCase):
    def test_success_and_metadata_mismatch_are_distinguished(self):
        spec=importlib.util.spec_from_file_location('avatar_result_tool',BASE/'avatar/scripts/test_avatar_api.py')
        tool=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool)
        names=['fit_anchor','fit_anchor_waist','fit_shoulder_L','fit_shoulder_R','fit_wrist_L','fit_wrist_R']
        doc={'scene':0,'scenes':[{'nodes':[0],'extras':{'fitme_measurements':{'height_cm':{'measured':175}}}}],
             'nodes':[{'name':'Body','children':list(range(1,7))}]+[{'name':name} for name in names]}
        encoded=json.dumps(doc).encode();encoded+=b' '*((-len(encoded))%4)
        glb=b'glTF'+struct.pack('<II',2,20+len(encoded))+struct.pack('<I4s',len(encoded),b'JSON')+encoded
        digest=hashlib.sha256(glb).hexdigest()
        parent,anchors,measures=extract(glb,'avatars')
        subject='explicit-test-account';owner=hashlib.sha256(subject.encode()).hexdigest()
        base=f'https://fitmemlstdev.blob.core.windows.net/body-glb/v2/avatars/{owner}/{digest}/'
        signature='?sp=r&sr=b&sig=never-log-this'
        receipt={'status':'ready','model_id':digest,'urls':{name:base+name+signature for name in ['model.glb','anchors.json','measurements.json']}}
        for corrupt in (False,True):
            metadata={'schema_version':1,'model_sha256':digest,'parent_node':parent,'anchors':anchors}
            if corrupt: metadata['parent_node']='wrong-model-root'
            payloads=[json.dumps(receipt).encode(),glb,json.dumps(metadata).encode(),
                      json.dumps({'schema_version':1,'model_sha256':digest,'measurements':measures}).encode()]
            with tempfile.TemporaryDirectory() as folder:
                photo=Path(folder)/'explicit.png';photo.write_bytes(b'\x89PNG\r\n\x1a\nfixture')
                output=Path(folder)/'result'
                argv=['test','--photo',str(photo),'--height-cm','175','--weight-kg','70','--subject',subject,'--output',str(output)]
                console=io.StringIO()
                with patch.object(sys,'argv',argv),patch.object(tool,'read_bytes',side_effect=payloads),contextlib.redirect_stdout(console):
                    status=tool.main()
                report=(output/'test-result.json').read_text()
                self.assertEqual(status,1 if corrupt else 0)
                self.assertEqual(json.loads(report)['status'],'failed' if corrupt else 'passed')
                self.assertNotIn('never-log-this',report+console.getvalue())
