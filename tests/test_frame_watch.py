# 역할: 실제 자식 프로세스의 프레임 정지 감지와 완료 후 감시 해제를 검사합니다.
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'garment/src'))
from core.frame_watch import FrameWatch, limit
from core.blender_process import run_blender, FrameTimeout


class FrameWatchTests(unittest.TestCase):
    def test_large_stdin_is_not_resent_or_truncated_after_poll_timeout(self):
        code="import sys,time; time.sleep(.3); print(len(sys.stdin.buffer.read()),flush=True)"
        payload=b'x'*(2*1024*1024)
        with tempfile.NamedTemporaryFile(suffix='.log',delete=False) as log:
            path=Path(log.name)
        try:
            with path.open('wb') as log:
                result=run_blender([sys.executable,'-u','-c',code],input=payload,stdout=log,
                    stderr=subprocess.STDOUT,env=dict(os.environ),pass_fds=(),timeout=4.)
            self.assertEqual(result.returncode,0)
            self.assertEqual(path.read_text().strip(),str(len(payload)))
        finally: path.unlink(missing_ok=True)

    def test_first_and_subsequent_limits_and_duplicate_events(self):
        watch=FrameWatch()
        watch.observe({'stage':'cloth_frame_start','frame':1},10.)
        watch.observe({'stage':'cloth_frame_start','frame':1},50.)
        self.assertIsNone(watch.expired(69.))
        self.assertEqual(watch.expired(70.)['frame'],1)
        watch.observe({'stage':'cloth_frame_complete','frame':1},71.)
        self.assertIsNone(watch.expired(1000.))
        watch.observe({'stage':'cloth_frame_start','frame':2},100.)
        watch.observe({'stage':'cloth_frame_complete','frame':1},101.)
        self.assertEqual(watch.expired(130.)['frame_limit_seconds'],30.)
        self.assertEqual(limit('nan',30.),30.)
        self.assertEqual(limit('-1',30.),30.)

    def test_real_child_hanging_frame_is_killed_before_global_timeout(self):
        code="import json,time; print('FITME_STAGE '+json.dumps({'stage':'cloth_frame_start','frame':2}),flush=True); time.sleep(5)"
        with tempfile.NamedTemporaryFile(suffix='.log',delete=False) as log:
            path=Path(log.name)
        started=time.monotonic()
        try:
            with path.open('wb') as log, self.assertRaises(FrameTimeout) as error:
                run_blender([sys.executable,'-u','-c',code],input=b'',stdout=log,
                    stderr=subprocess.STDOUT,env={**os.environ,'CLOTH_FRAME_TIMEOUT_SECONDS':'.2'},
                    pass_fds=(),timeout=4.)
            self.assertEqual(error.exception.details['frame'],2)
            self.assertLess(time.monotonic()-started,4.)
        finally: path.unlink(missing_ok=True)

    def test_completed_frame_does_not_timeout_during_export(self):
        code="import json,time; print('FITME_STAGE '+json.dumps({'stage':'cloth_frame_start','frame':2}),flush=True); print('FITME_STAGE '+json.dumps({'stage':'cloth_frame_complete','frame':2}),flush=True); time.sleep(.5)"
        with tempfile.NamedTemporaryFile(suffix='.log',delete=False) as log:
            path=Path(log.name)
        try:
            with path.open('wb') as log:
                result=run_blender([sys.executable,'-u','-c',code],input=b'',stdout=log,
                    stderr=subprocess.STDOUT,env={**os.environ,'CLOTH_FRAME_TIMEOUT_SECONDS':'.2'},
                    pass_fds=(),timeout=4.)
            self.assertEqual(result.returncode,0)
        finally: path.unlink(missing_ok=True)


if __name__ == '__main__': unittest.main()
