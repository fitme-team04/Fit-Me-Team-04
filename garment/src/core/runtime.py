# 역할: Blender 작업을 실행하고 생성된 GLB를 결과 Blob에 게시합니다.
"""Run on Linux with: uvicorn api:app --workers 1"""
import json
import base64
import logging
import math
import os
import subprocess
import threading
import tempfile
from pathlib import Path
from storage.blob_assets import publish
from core.cloth_checkpoint import interrupted_preview
from core.blender_process import run_blender, FrameTimeout

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[1]
SLOTS = threading.BoundedSemaphore(int(os.getenv('FITME_CONCURRENCY','1')))


def memory_file():
    create=getattr(os,'memfd_create',None)
    if create is not None:
        try:return os.fdopen(create('fitme-garment'),'w+b')
        except OSError:pass
    return tempfile.TemporaryFile(mode='w+b',dir='/dev/shm')


def render(payload, worker, path=None, subject=''):
    if not SLOTS.acquire(blocking=False):
        raise HTTPException(429,'Blender is busy',headers={'Retry-After':'5'})
    try:
        if payload.get('body_model_id'):
            from storage.body_asset import load_body
            payload = {**payload, 'body_glb_b64':base64.b64encode(
                load_body(subject, payload['body_model_id'])).decode('ascii')}
        # Anonymous Linux memory file, scoped to this request. No filesystem path.
        with memory_file() as out:
            fd=out.fileno()
            with tempfile.TemporaryDirectory(prefix='fitme-cloth-job-') as folder:
                checkpoint=Path(folder)/'last.glb'
                logs=Path(folder)/'blender.log'; logs.touch()
                env={**os.environ,'FITME_FD':str(fd),'FITME_CHECKPOINT':str(checkpoint),
                     'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'}
                fallback=None
                details=None
                try:
                    with logs.open('wb') as log:
                        proc=run_blender([os.getenv('BLENDER_BIN','blender'),'-t',
                            str(min(4,os.cpu_count() or 1)),'-b','-Y',
                            *([str(path)] if path else ['--factory-startup']),'--python-exit-code','3',
                            '-P',str(ROOT/'geometry'/worker)],input=json.dumps(payload).encode(),
                            stdout=log,stderr=subprocess.STDOUT,env=env,pass_fds=(fd,),
                            timeout=300 if payload.get('body_model_id') else 120)
                    if proc.returncode:
                        if checkpoint.is_file():
                            fallback='simulation_interrupted'
                        else:
                            lines=logs.read_text(errors='replace').splitlines()
                            for line in lines:
                                if line.startswith('FITME_INPUT_ERROR '):
                                    raise HTTPException(422,line.removeprefix('FITME_INPUT_ERROR '))
                            logging.error('FitMe Blender failed, exit %s: %s',proc.returncode,lines[-12:])
                            raise HTTPException(500,'Blender generation failed')
                except FrameTimeout as exc:
                    if not checkpoint.is_file(): raise
                    fallback='frame_timeout'; details=exc.details
                except subprocess.TimeoutExpired:
                    if not checkpoint.is_file(): raise
                    fallback='simulation_timeout'
                if fallback:
                    data=interrupted_preview(checkpoint.read_bytes(),fallback,details)
                    logging.warning('FITME_STAGE checkpoint_recovered reason=%s',fallback)
                else:
                    out.seek(0); data=out.read()
        if data[:4]!=b'glTF' or len(data)!=int.from_bytes(data[8:12],'little'):
            raise HTTPException(500,'Incomplete GLB')
        kind = 'avatars' if worker == 'worker.py' else 'garments'
        receipt = publish(data, kind, subject)
        return JSONResponse(receipt, headers={'Cache-Control':'private, no-store'})
    except subprocess.TimeoutExpired:
        raise HTTPException(504,'Blender timed out')
    except ValueError:
        raise HTTPException(503,'Collision body asset failed validation') from None
    except FileNotFoundError:
        raise HTTPException(503,'Blender executable unavailable')
    finally:
        SLOTS.release()
