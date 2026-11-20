# 역할: Blender 실행과 프레임 제한시간·로그를 부모 프로세스에서 관리합니다.
import json
import logging
from pathlib import Path
import subprocess
import threading
import time

from core.frame_watch import FrameWatch, limit


class FrameTimeout(subprocess.TimeoutExpired):
    def __init__(self, command, details):
        super().__init__(command,details['frame_limit_seconds'])
        self.details=details


def run_blender(command, *, input, stdout, stderr, env, pass_fds, timeout):
    """Use a parent-side deadline even while Blender is blocked in C/C++."""
    watch=FrameWatch(limit(env.get('CLOTH_FIRST_FRAME_TIMEOUT_SECONDS'),60.),
                     limit(env.get('CLOTH_FRAME_TIMEOUT_SECONDS'),30.))
    log_path=Path(stdout.name)
    started=time.monotonic()
    pending=''
    with log_path.open(encoding='utf-8',errors='replace') as reader, subprocess.Popen(
            command,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr,env=env,pass_fds=pass_fds) as process:
        def consume():
            nonlocal pending
            pending+=reader.read()
            lines=pending.split('\n'); pending=lines.pop()
            for line in lines:
                if not line.startswith('FITME_STAGE '): continue
                logging.warning('%s',line[:2000])
                try: event=json.loads(line[len('FITME_STAGE '):])
                except (ValueError,TypeError): continue
                if isinstance(event,dict): watch.observe(event,time.monotonic())
        # 입력은 별도 스레드가 끝까지 쓰고 stdin 을 닫는다. Python 3.12 의 communicate(timeout=...) 는
        # 재시도 때 input=None 이면 남은 입력을 더 쓰지 않아, 64KB 넘는 입력(신체 GLB)에서 Blender 가
        # stdin EOF 를 영원히 기다렸다 (3.13 에서는 고쳐짐).
        def feed():
            try:
                if input: process.stdin.write(input)
            except (BrokenPipeError, OSError, ValueError):
                pass
            finally:
                try: process.stdin.close()
                except (BrokenPipeError, OSError, ValueError): pass
        writer=threading.Thread(target=feed,daemon=True)
        writer.start()
        try:
            while True:
                try:
                    process.wait(timeout=.1)
                    consume()
                    return subprocess.CompletedProcess(command,process.returncode)
                except subprocess.TimeoutExpired:
                    pass
                consume()
                details=watch.expired(time.monotonic())
                if details is not None and process.poll() is None:
                    logging.warning('FITME_STAGE %s',json.dumps({'stage':'frame_timeout',**details}))
                    raise FrameTimeout(command,details)
                if time.monotonic()-started >= timeout:
                    raise subprocess.TimeoutExpired(command,timeout)
        finally:
            if process.poll() is None: process.kill()
            process.wait()
            writer.join(timeout=5)
