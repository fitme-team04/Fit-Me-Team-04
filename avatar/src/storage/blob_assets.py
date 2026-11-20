# 역할: 생성 결과를 비공개 Blob에 저장하고 사용자별 다운로드 URL을 발급합니다.
"""Publish immutable Blender results and issue short-lived links to individual blobs."""
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Literal

from azure.core.exceptions import AzureError, ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobSasPermissions, BlobServiceClient, ContentSettings, generate_blob_sas
from fastapi import APIRouter, Depends, Header, HTTPException, Path
from fastapi.responses import RedirectResponse

from geometry.mesh_anchors import extract, garment_fitting


def principal(x_fitme_subject: str = Header(default="", max_length=255)):
    if not x_fitme_subject.strip():
        raise HTTPException(401, "Authenticated ingress required")
    return x_fitme_subject


@lru_cache(maxsize=1)
def storage():
    url = os.getenv("AZURE_STORAGE_ACCOUNT_URL", "")
    name = os.getenv("AZURE_STORAGE_CONTAINER", "")
    if not url.startswith("https://") or not name:
        raise HTTPException(503, "Configure Blob Storage account and container")
    service = BlobServiceClient(url, credential=DefaultAzureCredential(), retry_total=2)
    return service, service.get_container_client(name)


def directory(kind, subject, digest):
    if kind == "avatars":
        owner = hashlib.sha256(subject.encode()).hexdigest()
        return f"v2/avatars/{owner}/{digest}"
    return f"v2/garments/{digest}"


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False).encode()


def read_links(service, container, prefix, names):
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=5)
    expiry = now + timedelta(minutes=15)
    key = service.get_user_delegation_key(start, expiry)
    links = {}
    for name in names:
        blob = container.get_blob_client(f"{prefix}/{name}")
        signature = generate_blob_sas(
            account_name=service.account_name, container_name=container.container_name,
            blob_name=blob.blob_name, user_delegation_key=key,
            permission=BlobSasPermissions(read=True), start=start, expiry=expiry, protocol="https",
        )
        links[name] = f"{blob.url}?{signature}"
    return links


def publish(glb, kind, subject):
    digest = hashlib.sha256(glb).hexdigest()
    prefix = directory(kind, subject, digest)
    parent, anchors, report = extract(glb, kind)
    metadata = dict(schema_version=1, model="model.glb", model_sha256=digest,
                    space="glTF parent-local", parent_node=parent, unit="m",
                    up_axis="+Y", quaternion_order="xyzw", anchors=anchors)
    if kind == "garments":
        metadata["garment"] = garment_fitting(glb)
    files = {"model.glb": (glb, "model/gltf-binary")}
    if kind == "avatars":
        if not report:
            raise ValueError("Missing body measurement report in GLB")
        files["measurements.json"] = (json_bytes(dict(schema_version=1, model_sha256=digest,
                                                      measurements=report)), "application/json")
    # Publish this completion marker after the model and any report.
    files["anchors.json"] = (json_bytes(metadata), "application/json")
    service, container = storage()
    try:
        for name, (data, mime) in files.items():
            blob = container.get_blob_client(f"{prefix}/{name}")
            try:
                blob.upload_blob(data, overwrite=False, content_settings=ContentSettings(
                    content_type=mime, cache_control="private, no-store"))
            except ResourceExistsError:
                pass  # A retry or concurrent publisher already wrote these immutable bytes.
        urls = read_links(service, container, prefix, files)
    except AzureError as exc:
        raise HTTPException(503, "Blob publication or link issuance failed") from exc
    return dict(status="ready", model_id=digest, urls=urls)


def downloads(kind):
    router = APIRouter()

    @router.get("/api/" + kind + "/{model_id}/{part}")
    def read(part: Literal["model.glb", "anchors", "measurements"],
             model_id: str = Path(pattern=r"^[a-f0-9]{64}$"), subject: str = Depends(principal)):
        name = {"model.glb": "model.glb", "anchors": "anchors.json", "measurements": "measurements.json"}[part]
        if part == "measurements" and kind != "avatars":
            raise HTTPException(404)
        prefix = directory(kind, subject, model_id)
        service, container = storage()
        try:
            if not container.get_blob_client(f"{prefix}/anchors.json").exists():
                raise HTTPException(404, "Model unavailable")
            url = read_links(service, container, prefix, [name])[name]
        except AzureError as exc:
            raise HTTPException(503, "Blob unavailable") from exc
        return RedirectResponse(url, status_code=307, headers={"Cache-Control": "private, no-store"})

    return router
