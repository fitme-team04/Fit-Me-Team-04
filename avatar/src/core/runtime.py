# 역할: Blender 작업을 실행하고 생성된 GLB를 결과 Blob에 게시합니다.
"""Run on Linux with: uvicorn api:app --workers 1"""
import json
import logging
import math
import os
import subprocess
import tempfile
import threading
from pathlib import Path
from storage.blob_assets import publish
from core.body_girths import body_girths

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[1]
SLOTS = threading.BoundedSemaphore(int(os.getenv('FITME_CONCURRENCY','1')))
def memory_file():
    create = getattr(os, 'memfd_create', None)
    if create is not None:
        try:
            fd = create('fitme-avatar')
        except OSError:
            pass
        else:
            return os.fdopen(fd, 'w+b')
    return tempfile.TemporaryFile(mode='w+b', dir='/dev/shm')


def render(payload, worker, path=None, subject=''):
    if not SLOTS.acquire(blocking=False):
        raise HTTPException(429,'Blender is busy',headers={'Retry-After':'5'})
    try:
        # Both paths use request-scoped memory-backed storage, closed after rendering.
        with memory_file() as out:
            fd=out.fileno()
            env={**os.environ,'FITME_FD':str(fd),'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'}
            proc=subprocess.run([os.getenv('BLENDER_BIN','blender'),'-t','1','-b','-Y',
                                 *([str(path)] if path else ['--factory-startup']),'--python-exit-code','3','-P',str(ROOT/'geometry'/worker)],
                                input=json.dumps(payload).encode(),stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,env=env,pass_fds=(fd,),timeout=120)
            if proc.returncode:
                lines=proc.stdout.decode(errors='replace').splitlines()
                for line in lines:
                    if line.startswith('FITME_INPUT_ERROR '):
                        raise HTTPException(422,line.removeprefix('FITME_INPUT_ERROR '))
                logging.error('FitMe Blender failed, exit %s: %s',proc.returncode,lines[-12:])
                raise HTTPException(500,'Blender generation failed')
            for line in getattr(proc,'stdout',b'').decode(errors='replace').splitlines():
                if line.startswith('FITME_ADJUSTMENT '):
                    logging.warning('%s', line)
            out.seek(0)
            data=out.read()
        if data[:4]!=b'glTF' or len(data)!=int.from_bytes(data[8:12],'little'):
            raise HTTPException(500,'Incomplete GLB')
        kind = 'avatars' if worker in ('worker.py', 'sam_avatar_worker.py') else 'garments'
        receipt = publish(data, kind, subject)
        if kind == 'avatars':
            receipt = {**receipt, **body_girths(payload)}
        return JSONResponse(receipt, headers={'Cache-Control':'private, no-store'})
    except subprocess.TimeoutExpired:
        raise HTTPException(504,'Blender timed out')
    except FileNotFoundError:
        raise HTTPException(503,'Blender executable unavailable')
    finally:
        SLOTS.release()
