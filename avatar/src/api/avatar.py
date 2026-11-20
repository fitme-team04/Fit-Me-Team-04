# 역할: SAM이 복원한 실제 메시를 키에 맞춰 정규화하고 GLB로 저장합니다.
from core.contract import prepare_prediction
from storage.blob_assets import principal, downloads
from fastapi import Depends
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from core.runtime import render
import httpx
import subprocess
import tempfile
import threading
import json
import logging
from core.contract import PREDICTION_KEYS
from core.features import make_features, validate_features
from core.ml_endpoint import endpoint_settings, request_headers
from core.test_prediction import prediction_mode, example_prediction
from core.photo import prepare_photo
from core.sam_runtime import resident, runtime_mode, SAMRuntimeError, SAMInputError
from core.error_logging import register_error_logging
from contextlib import asynccontextmanager
from fastapi import Request, Header
from starlette.concurrency import run_in_threadpool



ROOT = Path(__file__).resolve().parents[1]
@asynccontextmanager
async def lifespan(app):
    try:
        if runtime_mode() == 'resident':
            await run_in_threadpool(resident.start)
        yield
    finally:
        await run_in_threadpool(resident.stop)


app = FastAPI(title='FitMe male avatar', lifespan=lifespan)
register_error_logging(app)

app.include_router(downloads('avatars'))

job_slot = threading.BoundedSemaphore(1)

def photo_input_error(code):
    if code=='full_body_required':
        return HTTPException(422,{'code':code,
            'message':'머리부터 양발과 양손이 사진 안에 모두 보이도록 다시 촬영해 주세요.'})
    return HTTPException(422,{'code':'single_person_required',
        'message':'한 사람의 머리부터 양발까지 모두 보이는 사진을 촬영해 주세요.'})


def reconstruct(photo, folder):
    photo_file = folder / "photo"
    output = folder / "surface.npz"
    photo_file.write_bytes(photo)
    try:
        if runtime_mode() == 'resident':
            resident.infer(photo_file, output)
            return output
    except SAMInputError as exc:
        raise photo_input_error(exc.code) from exc
    except SAMRuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    try:
        proc = subprocess.run([os.getenv("SAM_PYTHON","/opt/sam-env/bin/python"),
                               str(ROOT/"inference"/"sam_reference.py"),"infer",str(photo_file),str(output)],
                              cwd=os.getenv("SAM_REPO","/opt/sam-body"),
                              stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240)
    except (FileNotFoundError,subprocess.TimeoutExpired) as exc:
        raise HTTPException(503,"SAM runtime unavailable or timed out") from exc
    if proc.returncode:
        if b"FITME_INPUT_ERROR" in proc.stdout:
            code='full_body_required' if b'FITME_INPUT_ERROR full_body_required' in proc.stdout else 'single_person_required'
            raise photo_input_error(code)
        raise HTTPException(503,"SAM inference failed")
    return output

def measure_surface(surface, template):
    try:
        proc = subprocess.run([
            os.getenv('BLENDER_BIN', '/opt/blender/blender'), '-b', '-Y', str(template),
            '--python-exit-code', '1', '-P', str(ROOT/'geometry'/'sam_measure_worker.py')],
            input=json.dumps({'surface_path': str(surface)}).encode(),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        if proc.returncode:
            raise ValueError('Surface measurement failed')
        lines = [line for line in proc.stdout.decode(errors='replace').splitlines()
                 if line.startswith('FITME_SAM_MEASUREMENTS ')]
        return json.loads(lines[-1].split(' ', 1)[1])
    except (OSError, subprocess.TimeoutExpired, ValueError, IndexError) as exc:
        raise HTTPException(503, 'SAM surface measurement unavailable') from exc


async def predict(features):
    payload = validate_features(features)
    try:
        mode = prediction_mode()
    except ValueError as exc:
        raise HTTPException(503, 'Invalid FITME_PREDICTION_MODE') from exc
    if mode == 'example':
        return example_prediction(payload['height_cm'])
    try:
        endpoint, auth, deployment = endpoint_settings()
        headers = await run_in_threadpool(request_headers, auth, deployment)
    except Exception as exc:
        raise HTTPException(503, 'Azure ML endpoint configuration or authentication unavailable') from exc
    try:
        async with httpx.AsyncClient(timeout=90, trust_env=False, follow_redirects=False) as client:
            response = await client.post(endpoint,json=payload,headers=headers)
            response.raise_for_status()
            result = response.json()
        return prepare_prediction(result, payload['height_cm'])
    except httpx.TimeoutException as exc:
        raise HTTPException(504,"Azure ML timed out") from exc
    except (httpx.HTTPError, ValueError, HTTPException) as exc:
        raise HTTPException(502,"Azure ML returned an invalid response") from exc

def ml_measurements_enabled(environment=None):
    value = (os.environ if environment is None else environment).get('FITME_ML_MEASUREMENTS', 'off').strip().lower()
    if value not in {'on', 'off'}:
        raise ValueError('FITME_ML_MEASUREMENTS must be on or off')
    return value == 'on'


async def ml_prediction(surface, template, height_cm, weight_kg):
    """SAM 몸 모양은 그대로 두고, Azure ML이 예측한 치수 28개를 핏 판정용 target으로만 붙입니다.

    FITME_ML_MEASUREMENTS=on 일 때만 동작합니다(기본 off). ML 호출이 실패하면 로그만 남기고
    None을 돌려주며, 웹은 SAM 측정값(measured)으로 판정합니다. 예시(example) 치수는 핏 판정에 쓰지 않습니다.
    """
    try:
        if not ml_measurements_enabled():
            return None
        if prediction_mode() != 'azure_ml':
            logging.warning('FITME_ML_MEASUREMENTS skipped: FITME_PREDICTION_MODE is not azure_ml')
            return None
        measures = await run_in_threadpool(measure_surface, surface, template)
        job = await predict(make_features(measures, height_cm, weight_kg))
    except (HTTPException, ValueError) as exc:
        logging.warning('FITME_ML_MEASUREMENTS skipped: %s', getattr(exc, 'detail', exc))
        return None
    return {key: float(job['male'][key]) for key in PREDICTION_KEYS}


@app.post("/api/avatars",response_class=JSONResponse)
async def avatar(request:Request,height_cm:float=Header(gt=0,allow_inf_nan=False),
                 weight_kg:float=Header(gt=0,allow_inf_nan=False), subject:str=Depends(principal)):
    data = bytearray()
    async for chunk in request.stream():
        if len(data)+len(chunk)>3*1024*1024:
            raise HTTPException(413,"Photo exceeds 3 MiB")
        data.extend(chunk)
    template = Path(os.getenv("FITME_TEMPLATE","/models/fitme_depth_fixed.blend"))
    if not template.is_file():
        raise HTTPException(503,"Missing SAM landmark guide template")
    if not job_slot.acquire(blocking=False):
        raise HTTPException(429,"Avatar generator busy",headers={"Retry-After":"5"})
    try:
        from PIL import Image
        try:
            photo = await run_in_threadpool(prepare_photo, bytes(data))
        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            raise HTTPException(422, 'Invalid JPEG/PNG photo or source exceeds 64 megapixels') from exc
        with tempfile.TemporaryDirectory(dir="/dev/shm") as temp:
            surface = await run_in_threadpool(reconstruct, photo, Path(temp))
            job = {'surface_path':str(surface), 'height_cm':height_cm}
            prediction = await ml_prediction(surface, template, height_cm, weight_kg)
            if prediction is not None:
                job['male'] = prediction
            return await run_in_threadpool(render, job, 'sam_avatar_worker.py', template, subject)
    finally:
        job_slot.release()


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok", "service": "avatar", "body_geometry_source":"sam_surface",
            "photo_framing_check":"sam_projected_full_body_v1",
            "ml_measurements":os.getenv('FITME_ML_MEASUREMENTS','off').strip().lower(),
            "source_revision":os.getenv('FITME_SOURCE_REVISION')}
