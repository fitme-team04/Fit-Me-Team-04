# 역할: 신체 성공 응답은 ML 원값을 전달하고 HTTP·검증·예외 실패는 둘레를 null로 내보내는지 검사합니다.
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'avatar/src'))
from core import runtime
from core.body_girths import GIRTH_KEYS
from core.error_logging import register_error_logging


class BodyGirthResponseTests(unittest.TestCase):
    def test_success_uses_ml_values_not_mesh_report(self):
        values={'chest_girth_cm':100.1,'waist_girth_cm':80.2,'hip_girth_cm':96.3}
        glb=b'glTF'+(2).to_bytes(4,'little')+(12).to_bytes(4,'little')
        def blender(*args,**kwargs):
            os.write(kwargs['pass_fds'][0],glb)
            return types.SimpleNamespace(returncode=0,stdout=b'')
        with tempfile.TemporaryFile() as out, patch.object(runtime,'memory_file',return_value=out), \
             patch.object(runtime.subprocess,'run',side_effect=blender), \
             patch.object(runtime,'publish',return_value={'status':'ready','urls':{'model.glb':'example'}}):
            response=runtime.render({'male':values},'worker.py',subject='test')
        result=json.loads(response.body)
        self.assertEqual({k:result[k] for k in GIRTH_KEYS},values)
        self.assertEqual(result['urls']['model.glb'],'example')

    def test_failure_preserves_status_detail_headers_and_nulls(self):
        app=FastAPI();register_error_logging(app)
        @app.post('/api/avatars')
        def avatar(status:int):
            if status==500:raise RuntimeError('private')
            raise HTTPException(status,'failure',headers={'Retry-After':'5'})
        client=TestClient(app,raise_server_exceptions=False)
        for status in (401,413,422,429,500,503,504):
            response=client.post('/api/avatars',params={'status':status})
            self.assertEqual(response.status_code,status)
            self.assertEqual({k:response.json()[k] for k in GIRTH_KEYS},dict.fromkeys(GIRTH_KEYS))
            if status!=500:self.assertEqual(response.headers['retry-after'],'5')
            self.assertEqual(len(response.content),int(response.headers['content-length']))
        response=client.post('/api/avatars',params={'status':'bad'})
        self.assertEqual(response.status_code,422)
        self.assertEqual({k:response.json()[k] for k in GIRTH_KEYS},dict.fromkeys(GIRTH_KEYS))


if __name__ == '__main__':
    unittest.main()
