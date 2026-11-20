# 역할: SAM GPU 프로세스를 상주시켜 모델을 재사용하고 실패·시간 초과 시 정리합니다.
import json
import logging
import os
from pathlib import Path
import queue
import subprocess
import threading
import time


class SAMRuntimeError(RuntimeError):
    pass


class SAMInputError(ValueError):
    def __init__(self, message='Expected one visible person', *, code='single_person_required'):
        super().__init__(message)
        self.code=code if code in ('single_person_required','full_body_required') else 'single_person_required'


def runtime_mode():
    mode = os.getenv('SAM_RUNTIME_MODE', 'resident')
    if mode not in {'resident', 'oneshot'}:
        raise SAMRuntimeError('SAM_RUNTIME_MODE must be resident or oneshot')
    return mode


class ResidentSAM:
    def __init__(self):
        self.process = None
        self.replies = None
        self.lock = threading.Lock()

    @staticmethod
    def _read(process, replies):
        try:
            for line in process.stdout:
                if line.startswith('FITME_SAM_REPLY '):
                    try:
                        reply = json.loads(line.split(' ', 1)[1])
                        replies.put(reply if isinstance(reply, dict) else {'status':'protocol_error'})
                    except ValueError:
                        replies.put({'status':'protocol_error'})
                elif line.startswith('FITME_SAM_FAILURE '):
                    logging.error('Resident SAM failed: %s', line.strip().split()[-1])
                elif line.startswith('FITME_PHOTO_REJECTED '):
                    reason=line.strip().removeprefix('FITME_PHOTO_REJECTED ')
                    if reason in ('invalid_image_shape','missing_body_evidence','invalid_bbox',
                                  'invalid_keypoints','person_touches_image_boundary',
                                  'required_keypoints_outside_image','required_keypoints_outside_person_box'):
                        logging.warning('SAM photo rejected: %s',reason)
        finally:
            replies.put({'status':'exited'})

    def _stop(self):
        process, self.process = self.process, None
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        process.stdin.close()
        process.stdout.close()

    def stop(self):
        with self.lock:
            self._stop()

    def _reply(self):
        try:
            return self.replies.get(timeout=240)
        except queue.Empty as exc:
            self._stop()
            raise SAMRuntimeError('SAM worker timed out') from exc

    def _start(self):
        if self.process is not None and self.process.poll() is None:
            return
        self._stop()
        started = time.monotonic()
        script = Path(__file__).resolve().parents[1]/'inference/sam_reference.py'
        try:
            self.process = subprocess.Popen(
                [os.getenv('SAM_PYTHON','/opt/sam-env/bin/python'), '-u', str(script), 'serve'],
                cwd=os.getenv('SAM_REPO','/opt/sam-body'), stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace',
            )
        except OSError as exc:
            raise SAMRuntimeError('SAM runtime unavailable') from exc
        self.replies = queue.Queue()
        threading.Thread(target=self._read, args=(self.process,self.replies), daemon=True).start()
        if self._reply().get('status') != 'ready':
            self._stop()
            raise SAMRuntimeError('SAM worker initialization failed')
        logging.getLogger('uvicorn.error').info('Resident SAM model loaded; ready for reuse (%.2fs)',
                                               time.monotonic()-started)

    def start(self):
        with self.lock:
            self._start()

    def infer(self, photo, output):
        with self.lock:
            self._start()
            try:
                self.process.stdin.write(json.dumps({'photo':str(photo),'output':str(output)})+'\n')
                self.process.stdin.flush()
            except OSError as exc:
                self._stop()
                raise SAMRuntimeError('SAM worker communication failed') from exc
            reply = self._reply()
            status = reply.get('status')
            if status == 'input_error':
                raise SAMInputError(code=reply.get('code'))
            if status != 'ok' or not Path(output).is_file():
                self._stop()
                raise SAMRuntimeError('SAM inference failed')


resident = ResidentSAM()
