"""Redis consumers for DB work and garment/model processing. Launch individually or in FastAPI."""
import logging
import os
import socket
import sys
import threading
import time
import uuid

import redis
from fastapi import HTTPException
from pydantic import ValidationError

from v2_bus import GROUP, LANES, PAIR_TTL, PREFIX, TTL, connection, json_bytes, pair_vm_timeout
from v2_operations import dispatch

log = logging.getLogger("uvicorn.error")


def handle(client, lane, stream, message, fields):
    job = fields[b"id"].decode()
    paired = lane == "pair"
    key = f"{PREFIX}:{'pair-job' if paired else 'job'}:{job}"
    body = client.get(key)
    # A retried delivery may already have a committed reply.
    if body is not None and not client.exists(key + ":result"):
        operation = fields[b"op"].decode()
        try:
            data = dispatch(lane, operation, body, job)
            binary = operation == "get_model"
            result = {"status":200, "media":"model/gltf-binary" if binary else "application/json",
                      "body":data if binary else json_bytes(data)}
        except HTTPException as exc:
            result = {"status":exc.status_code, "media":"application/json", "body":json_bytes({"detail":exc.detail})}
        except (ValidationError, ValueError, UnicodeError):
            result = {"status":422, "media":"application/json", "body":json_bytes({"detail":"요청한 데이터를 확인해 주세요."})}
        except Exception as exc:
            # No request body, credentials or upstream URL in logs.
            log.error("V2 worker %s failed (%s)", operation, type(exc).__name__)
            result = {"status":503, "media":"application/json", "body":json_bytes({"detail":"처리 서버에 연결할 수 없어요. 잠시 후 다시 시도해 주세요."})}
        with client.pipeline() as pipe:
            pipe.hset(key + ":result", mapping=result)
            pipe.expire(key + ":result", PAIR_TTL if paired else TTL)
            if paired:
                pipe.expire(key + ":digest", PAIR_TTL)
                pipe.expire(key + ":owner", PAIR_TTL)
            else:
                pipe.rpush(key + ":ready", 1)
                pipe.expire(key + ":ready", TTL)
            pipe.delete(key)
            pipe.xack(stream, GROUP, message)
            pipe.xdel(stream, message)
            pipe.execute()
    else:
        with client.pipeline() as pipe:
            pipe.xack(stream, GROUP, message).xdel(stream, message).execute()


def consume(lane, stop):
    name = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    stream = f"{PREFIX}:{lane}:requests"
    # Body generation and cloth generation now run sequentially. Do not reclaim
    # an active job while the second VM is still simulating its garment.
    lease = max(65, 2 * pair_vm_timeout() + 65) if lane == "pair" else 65
    client = connection()
    try:
        while not stop.is_set():
            try:
                try:
                    client.xgroup_create(stream, GROUP, id="0", mkstream=True)
                except redis.ResponseError as exc:
                    if "BUSYGROUP" not in str(exc):
                        raise
                next_claim = 0
                while not stop.is_set():
                    client.set(f"{PREFIX}:{lane}:online", "1", ex=lease)
                    if time.monotonic() >= next_claim:
                        _, pending, *_ = client.xautoclaim(stream, GROUP, name, lease * 1000, "0-0", count=1)
                        for msg, fields in pending:
                            handle(client, lane, stream, msg, fields)
                        next_claim = time.monotonic() + 10
                    batches = client.xreadgroup(GROUP, name, {stream:">"}, count=1, block=1000)
                    for _, messages in batches:
                        for msg, fields in messages:
                            handle(client, lane, stream, msg, fields)
            except redis.RedisError:
                if not stop.is_set():
                    log.warning("V2 %s worker waiting for Redis", lane)
                stop.wait(2)
    finally:
        client.close()


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in LANES:
        raise SystemExit("Usage: python v2_worker.py db|media")
    stop = threading.Event()
    # A long Blender job gets its own queue. Photo measurements stay available on this host.
    if sys.argv[1] == "media":
        threading.Thread(target=consume, args=("pair", stop), daemon=True).start()
    try:
        consume(sys.argv[1], stop)
    finally:
        stop.set()
