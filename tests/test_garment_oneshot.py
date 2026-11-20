# 역할: 의류 서버가 모델 캐시만 준비하고 Blender는 요청별 실행·종료 경로로 처리하는지 검사합니다.
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'garment/src'))
from api import garments
from core import runtime


class GarmentOneshotTests(unittest.TestCase):
    def test_startup_downloads_without_starting_blender(self):
        with patch.object(garments,'ensure_models') as cache,patch('subprocess.Popen') as start:
            with TestClient(garments.app) as client:
                self.assertEqual(client.get('/health').status_code,200)
            cache.assert_called_once();start.assert_not_called()

    def test_each_request_runs_blender_and_closes_output(self):
        blob=b'glTF'+(2).to_bytes(4,'little')+(12).to_bytes(4,'little')
        descriptors=[]
        def blender(*args,**kwargs):
            fd=kwargs['pass_fds'][0];descriptors.append(fd);os.write(fd,blob)
            return types.SimpleNamespace(returncode=0,stdout=b'')
        for _ in range(2):
            with tempfile.TemporaryFile() as out,patch.object(runtime,'memory_file',return_value=out), \
                 patch.object(runtime,'run_blender',side_effect=blender) as run, \
                 patch.object(runtime,'publish',return_value={'status':'ready'}), \
                 patch('subprocess.Popen') as resident:
                self.assertEqual(runtime.render({},'garment_worker.py').status_code,200)
                run.assert_called_once();resident.assert_not_called()
            with self.assertRaises(OSError):os.fstat(descriptors[-1])


if __name__=='__main__':unittest.main()
