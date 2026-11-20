# 역할: SAM 상주 프로세스 재사용·재시작과 비밀 없는 오류 로깅을 검사합니다.
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'avatar/src'))
from core.sam_runtime import ResidentSAM, SAMInputError, SAMRuntimeError
from core.photo_visibility import validate_full_body


class ResidentTests(unittest.TestCase):
    def test_photo_rejection_logging_accepts_only_known_reason_codes(self):
        process=MagicMock();process.stdout=[
            'FITME_PHOTO_REJECTED private/photo/path\n',
            'FITME_PHOTO_REJECTED person_touches_image_boundary\n']
        replies=queue.Queue()
        with self.assertLogs(level='WARNING') as captured:
            ResidentSAM._read(process,replies)
        self.assertEqual(len(captured.output),1)
        self.assertIn('person_touches_image_boundary',captured.output[0])
        self.assertNotIn('private',captured.output[0])

    def test_cropped_person_is_rejected_before_canonical_rig_and_mesh_write(self):
        import importlib.util
        import numpy as np
        spec=importlib.util.spec_from_file_location('sam_reference_crop_test',
            Path(__file__).resolve().parents[1]/'avatar/src/inference/sam_reference.py')
        module=importlib.util.module_from_spec(spec)
        cv2=MagicMock();cv2.imread.return_value=np.zeros((800,600,3),dtype=np.uint8)
        with patch.dict(sys.modules,{'cv2':cv2,'torch':MagicMock()}):
            spec.loader.exec_module(module)
        estimator=MagicMock();estimator.process_one_image.return_value=[{
            'bbox':np.array([50.,0.,550.,799.]),'pred_keypoints_2d':np.full((70,2),200.)}]
        rig=MagicMock()
        with patch.object(module.np,'savez_compressed') as write:
            with self.assertRaises(module.InputError) as error:
                module.infer_photo((estimator,rig,None,None,None,None),'photo','output')
        self.assertEqual(error.exception.code,'full_body_required')
        rig.assert_not_called();write.assert_not_called()

    def test_no_person_is_recoverable_in_reference_inference(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('sam_reference_test',
            Path(__file__).resolve().parents[1]/'avatar/src/inference/sam_reference.py')
        module=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'cv2':MagicMock(),'numpy':MagicMock(),'torch':MagicMock()}):
            spec.loader.exec_module(module)
        estimator=MagicMock()
        estimator.process_one_image.return_value=[]
        with self.assertRaises(module.InputError):
            module.infer_photo((estimator,None,None,None,None,None),'photo','output')

    def test_api_startup_preloads_once_and_shutdown_stops_worker(self):
        import importlib
        api=importlib.import_module('api.avatar')
        for mode in ('resident','oneshot'):
            with patch.dict('os.environ',{'SAM_RUNTIME_MODE':mode}), \
                 patch.object(api.resident,'start') as start, \
                 patch.object(api.resident,'stop') as stop:
                with TestClient(api.app) as client:
                    self.assertEqual(client.get('/health').status_code,200)
                    self.assertEqual(client.get('/health').status_code,200)
                self.assertEqual(start.call_count,1 if mode=='resident' else 0)
                stop.assert_called_once()

    def test_reuse_input_failure_crash_and_timeout_recovery(self):
        original = subprocess.Popen
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder)/'fake_sam.py'
            script.write_text('''import json,sys
from pathlib import Path
print('FITME_SAM_REPLY '+json.dumps({'status':'ready'}),flush=True)
for line in sys.stdin:
    job=json.loads(line)
    if job['photo']=='crash':sys.exit(1)
    if job['photo'] in ('bad','cropped'):status='input_error'
    else:
        Path(job['output']).write_bytes(b'mesh')
        status='ok'
    print('FITME_SAM_REPLY '+json.dumps({'status':status,'code':'full_body_required' if job['photo']=='cropped' else 'single_person_required'}),flush=True)
''',encoding='utf-8')
            def spawn(command, **kwargs):
                kwargs['cwd'] = folder
                return original([sys.executable,'-u',str(script)], **kwargs)
            worker = ResidentSAM()
            with patch('core.sam_runtime.subprocess.Popen',side_effect=spawn) as factory:
                try:
                    worker.start()
                    pid = worker.process.pid
                    output = Path(folder)/'surface.npz'
                    worker.infer('photo',output)
                    worker.infer('photo',output)
                    self.assertEqual(worker.process.pid,pid)
                    self.assertEqual(factory.call_count,1)
                    with self.assertRaises(SAMInputError):
                        worker.infer('bad',output)
                    with self.assertRaises(SAMInputError) as cropped:
                        worker.infer('cropped',output)
                    self.assertEqual(cropped.exception.code,'full_body_required')
                    self.assertEqual(worker.process.pid,pid)
                    with self.assertRaises(SAMRuntimeError):
                        worker.infer('crash',output)
                    self.assertIsNone(worker.process)
                    worker.infer('photo',output)
                    self.assertEqual(factory.call_count,2)
                    with patch.object(worker.replies,'get',side_effect=queue.Empty):
                        with self.assertRaises(SAMRuntimeError):
                            worker.infer('photo',output)
                    self.assertIsNone(worker.process)
                    worker.infer('photo',output)
                    self.assertEqual(factory.call_count,3)
                finally:
                    worker.stop()
            self.assertIsNone(worker.process)
