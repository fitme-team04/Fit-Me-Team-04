"""V2 HTTP gateway. Dynamic requests and worker replies use Redis."""
import hmac
import json
import threading
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError
from starlette.concurrency import run_in_threadpool

import garment_measurement
import model_pair
import settings
import v2_bus
from listing_fit import EaseRequest, ListingFitRequest
from v2_store import Listing, OpaqueID

STATIC = Path(__file__).resolve().parent / "static"
PAIR_UPLOAD_LIMIT = 4 * 1024 * 1024 + 4096  # 3 MiB JPEG/PNG as Base64, plus JSON metadata.


def model_subject(request):
    # When an ASGI authentication middleware is installed, its verified identity is authoritative.
    user = request.scope.get("user")
    if user is not None and user.is_authenticated:
        subject = user.identity
    else:
        secret = settings.get("V2_MODEL_INGRESS_TOKEN")
        supplied = request.headers.get("X-FitMe-Ingress-Token", "")
        if not secret or not hmac.compare_digest(secret.encode(), supplied.encode()):
            return None
        subject = request.headers.get("X-FitMe-Subject", "")
    if isinstance(subject, str) and subject == subject.strip() and 1 <= len(subject) <= 255 and subject.isascii() and subject.isprintable():
        return subject
    return None


def require_model_subject(request):
    subject = model_subject(request)
    if subject is None:
        raise HTTPException(401, "로그인된 팀 서비스에서 3D 보기를 열어 주세요.")
    return subject


@asynccontextmanager
async def lifespan(_app):
    stop = threading.Event()
    threads = []
    if settings.get("V2_EMBEDDED_WORKERS", "true").lower() in {"1", "true", "yes"}:
        from v2_worker import consume
        for lane in v2_bus.LANES:
            thread = threading.Thread(target=consume, args=(lane, stop), daemon=True, name="fitme-" + lane)
            thread.start()
            threads.append(thread)
    try:
        yield
    finally:
        stop.set()
        for thread in threads:
            await run_in_threadpool(thread.join, 2)


app = FastAPI(title="입어봄 V2", version="2.0.0", lifespan=lifespan)


def relay(lane, op, payload):
    return v2_bus.request(lane, op, v2_bus.json_bytes(payload))


@app.get("/api/health")
def health():
    return relay("db", "health", {})


@app.get("/api/resale/search")
def search(q: str = Query(min_length=1, max_length=400)):
    return relay("db", "search", {"q":q})


@app.get("/api/resale/garments/{garment_id}")
def chart(garment_id: int):
    return relay("db", "chart", {"garment_id":garment_id})


@app.post("/api/resale/ease")
def ease(body: EaseRequest):
    return relay("db", "ease", body.model_dump(mode="json"))


@app.post("/api/resale/recommend")
def fit(body: ListingFitRequest):
    return relay("db", "recommend", body.model_dump(mode="json"))


@app.get("/api/resale/measurement/status")
def measurement_status():
    return relay("media", "status", {})


@app.get("/api/resale/measurement/sample")
def measurement_sample():
    return relay("media", "sample", {})


@app.post("/api/resale/measurement")
async def measure(req: Request):
    if req.headers.get("content-type","").partition(";")[0].strip().lower() != "image/jpeg":
        raise HTTPException(415, "JPEG 사진을 보내 주세요.")
    photo = await garment_measurement.bounded_body(req, garment_measurement.MAX_PHOTO_BYTES)
    if not photo.startswith(b"\xff\xd8\xff") or not photo.endswith(b"\xff\xd9"):
        raise HTTPException(415, "JPEG 사진을 확인할 수 없어요.")
    return await run_in_threadpool(v2_bus.request, "media", "measure", photo)


@app.post("/api/resale/measurement/result")
async def import_result(req: Request):
    if req.headers.get("content-type","").partition(";")[0].strip().lower() != "application/json":
        raise HTTPException(415, "의류 측정 JSON을 보내 주세요.")
    data = await garment_measurement.bounded_body(req, garment_measurement.MAX_RESULT_BYTES)
    return await run_in_threadpool(v2_bus.request, "media", "import", data)


@app.post("/api/v2/listings")
def save_listing(card: Listing, idempotency_key: Annotated[uuid.UUID | None, Header()] = None):
    key = (idempotency_key or uuid.uuid4()).hex
    data = {"key":key, "card":card.model_dump(mode="json",exclude_none=True)}
    if card.catalogSelection:
        if idempotency_key:
            existing = relay("db", "listing_replay", data)
            if existing.status_code != 200 or json.loads(existing.body).get("id"):
                return existing
        checked = relay("media", "check_catalog_selection", card.catalogSelection.model_dump())
        if checked.status_code != 200:
            return checked
    return relay("db", "save_listing", data)


@app.get("/api/v2/listings/{listing_id}")
def get_listing(listing_id: OpaqueID):
    return relay("db", "get_listing", {"id":listing_id})


@app.get("/api/v2/models/{asset_id}")
def get_model(asset_id: OpaqueID):
    return relay("media", "get_model", {"id":asset_id})


@app.get("/api/v2/model-pair/status")
def model_pair_status(request: Request):
    result = relay("media", "pair_status", {})
    if result.status_code != 200:
        return result
    return JSONResponse({**json.loads(result.body), "authenticated":model_subject(request) is not None},
                        headers={"Cache-Control":"no-store"})


@app.get("/api/v2/garment-catalog")
def garment_catalog():
    return relay("media", "garment_catalog", {})


@app.get("/api/v2/garment-catalog/{garment_id}/sizes")
def garment_catalog_sizes(garment_id: int):
    if garment_id <= 0:
        raise HTTPException(422, "상품 ID를 확인해 주세요.")
    return relay("media", "garment_catalog_sizes", {"garment_id":garment_id})


@app.post("/api/v2/model-pair")
async def make_model_pair(request: Request, idempotency_key: Annotated[uuid.UUID | None, Header()] = None):
    subject = require_model_subject(request)
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        raise HTTPException(415, "사진과 모델 요청 정보를 JSON으로 보내 주세요.")
    raw = await garment_measurement.bounded_body(request, PAIR_UPLOAD_LIMIT)
    try:
        body = model_pair.ModelPairRequest.model_validate_json(raw)
    except ValidationError:
        # A normal Pydantic 422 may echo the submitted body photograph in error.input.
        raise HTTPException(422, "사진 형식·크기와 체형 입력, 상품 및 사이즈 선택을 확인해 주세요.") from None
    payload = body.model_dump(mode="json")
    data = v2_bus.json_bytes({"input":payload, "subject":subject})
    return await run_in_threadpool(v2_bus.submit_pair, data, idempotency_key, subject)


@app.get("/api/v2/model-pair/jobs/{job_id}")
def poll_model_pair(job_id: OpaqueID, request: Request):
    return v2_bus.poll_pair(job_id, require_model_subject(request))


class ProductQuery(BaseModel):
    link: str
    region: str | None = "KR"


class LabFit(BaseModel):
    item_code: str
    region: str = "KR"
    gender: str
    height_cm: float
    weight_kg: float
    measures: dict[str, float] | None = None
    my_garment: dict[str, float] | None = None


@app.post("/api/product/resolve")
def resolve_product(body: ProductQuery):
    return relay("db", "legacy_resolve", body.model_dump())


@app.get("/api/products")
def products():
    return relay("db", "legacy_products", {})


@app.post("/api/recommend")
def lab_recommend(body: LabFit):
    return relay("db", "legacy_fit", body.model_dump())


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
