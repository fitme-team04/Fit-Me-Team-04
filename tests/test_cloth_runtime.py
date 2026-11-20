# 역할: Blender 중단·시간 초과 때 마지막 옷 GLB를 복구하는 경로를 검사합니다.
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

from fastapi import HTTPException

SRC=Path(__file__).resolve().parents[1]/'garment/src'
sys.path.insert(0,str(SRC))


def fixture(mode='db_cloth_collision'):
    doc={'scene':0,'scenes':[{'extras':{'fitme_garment':{'fitting_mode':mode},
         'cloth_simulation':{'status':'failed','failure_reasons':['simulation_incomplete'],'frames':4,
                             'body_sizing':{'spring_reference':'sam_sized_template'} if mode=='sam_body_cloth_collision' else {}}}}]}
    header=json.dumps(doc).encode(); header+=b' '*(-len(header)%4)
    chunks=struct.pack('<I4s',4,b'BIN\0')+b'abcd'
    return struct.pack('<4sII',b'glTF',2,20+len(header)+len(chunks))+struct.pack('<I4s',len(header),b'JSON')+header+chunks


class RuntimeRecoveryTests(unittest.TestCase):
    def load_runtime(self, capture):
        storage=ModuleType('storage.blob_assets')
        def publish(data,kind,subject):
            size=struct.unpack_from('<I',data,12)[0]
            capture.update(json.loads(data[20:20+size])['scenes'][0]['extras'])
            return {'status':'error','preview_available':True}
        storage.publish=publish
        with patch.dict(sys.modules,{'storage.blob_assets':storage}):
            spec=importlib.util.spec_from_file_location('cloth_runtime_test',SRC/'core/runtime.py')
            module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    def test_timeout_and_crash_publish_last_complete_frame(self):
        for mode,outcome in ((mode,outcome) for mode in ('db_cloth_collision','sam_body_cloth_collision')
                             for outcome in ('timeout','crash','frame_timeout')):
            capture={}; runtime=self.load_runtime(capture)
            def run(command,**kwargs):
                Path(kwargs['env']['FITME_CHECKPOINT']).write_bytes(fixture(mode))
                if outcome == 'timeout': raise subprocess.TimeoutExpired(command,300)
                if outcome == 'frame_timeout':
                    raise runtime.FrameTimeout(command,{'frame':9,'frame_elapsed_seconds':30.1,'frame_limit_seconds':30.})
                return subprocess.CompletedProcess(command,3)
            with self.subTest(mode=mode,outcome=outcome), tempfile.TemporaryFile() as output, \
                    patch.object(runtime.os,'memfd_create',side_effect=lambda _:os.dup(output.fileno()),create=True), \
                    patch.object(runtime,'run_blender',side_effect=run):
                response=runtime.render({},'garment_worker.py',subject='owner')
            self.assertEqual(response.status_code,200)
            self.assertEqual(json.loads(response.body)['status'],'error')
            report=capture['cloth_simulation']
            self.assertEqual(report['frames'],4)
            reason={'timeout':'simulation_timeout','crash':'simulation_interrupted','frame_timeout':'frame_timeout'}[outcome]
            self.assertIn(reason,report['failure_reasons'])
            self.assertEqual(capture['fitme_garment']['fitting_mode'],mode)
            if mode=='sam_body_cloth_collision':
                self.assertEqual(report['body_sizing']['spring_reference'],'sam_sized_template')
            if outcome == 'frame_timeout': self.assertEqual(report['interruption']['frame'],9)

    def test_timeout_without_checkpoint_remains_error(self):
        runtime=self.load_runtime({})
        with tempfile.TemporaryFile() as output, \
                patch.object(runtime.os,'memfd_create',side_effect=lambda _:os.dup(output.fileno()),create=True), \
                patch.object(runtime,'run_blender',side_effect=subprocess.TimeoutExpired('blender',300)), \
                self.assertRaises(HTTPException) as error:
            runtime.render({},'garment_worker.py',subject='owner')
        self.assertEqual(error.exception.status_code,504)


if __name__ == '__main__': unittest.main()
