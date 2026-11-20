"""Correlate one HTTP request with its worker's reply using Redis Streams."""
import json
import hashlib
import uuid

import redis
from fastapi import HTTPException
from starlette.responses import JSONResponse, Response

import settings

PREFIX = "fitme:v2"
GROUP = "workers"
TTL = 100
LANES = ("db", "media", "pair")
PAIR_TTL = 1800
# Keep only request state in Redis. GLB files are downloaded from Blob by the viewer.
REGISTER_PAIR = """
local digest = redis.call('GET', KEYS[1])
if digest then
    if digest == ARGV[1] then return 1 else return 2 end
end
if redis.call('EXISTS', KEYS[4]) == 0 then return 3 end
if redis.call('XLEN', KEYS[3]) >= 100 then return 4 end
redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[4])
redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[4])
redis.call('SET', KEYS[5], ARGV[5], 'EX', ARGV[4])
redis.call('XADD', KEYS[3], '*', 'id', ARGV[3], 'op', 'generate_pair')
return 0
"""


def pair_vm_timeout():
    try:
        seconds = int(settings.get("MODEL_PAIR_VM_TIMEOUT_SECONDS", "420"))
    except ValueError:
        seconds = 420
    return max(1, min(seconds, 600))


def pair_accepted(job):
    return JSONResponse({"job_id": job, "status": "processing",
                         "status_url": f"/api/v2/model-pair/jobs/{job}"},
                        status_code=202, headers={"Retry-After": "2", "Cache-Control": "no-store"})


def owner_hash(subject):
    return hashlib.sha256(subject.encode("utf-8")).hexdigest()


def submit_pair(data, token, subject):
    owner = owner_hash(subject)
    job = hashlib.blake2b((token or uuid.uuid4()).bytes, key=bytes.fromhex(owner), digest_size=16).hexdigest()
    key = f"{PREFIX}:pair-job:{job}"
    digest = hashlib.sha256(data).hexdigest()
    try:
        with connection() as client:
            result = client.eval(REGISTER_PAIR, 5, key + ":digest", key,
                                 f"{PREFIX}:pair:requests", f"{PREFIX}:pair:online", key + ":owner",
                                 digest, data, job, PAIR_TTL, owner)
    except redis.RedisError as exc:
        raise HTTPException(503, "3D 요청을 전달할 수 없어요.") from exc
    if result == 2:
        raise HTTPException(409, "입력값이 달라졌어요. 새 요청으로 다시 시작해 주세요.")
    if result == 3:
        raise HTTPException(503, "3D 처리 서버 연결을 기다리고 있어요.")
    if result == 4:
        raise HTTPException(503, "3D 요청이 밀려 있어요. 잠시 뒤 다시 시도해 주세요.")
    return pair_accepted(job)


def poll_pair(job, subject):
    key = f"{PREFIX}:pair-job:{job}"
    try:
        with connection() as client, client.pipeline() as pipe:
            pipe.get(key + ":owner")
            pipe.hmget(key + ":result", "status", "media", "body")
            owner, (status, media, body) = pipe.execute()
    except redis.RedisError as exc:
        raise HTTPException(503, "3D 처리 결과를 확인할 수 없어요.") from exc
    if owner != owner_hash(subject).encode("ascii"):
        raise HTTPException(404, "요청을 찾을 수 없거나 결과 보관 시간이 지났어요.")
    if status and body is not None:
        return Response(body, status_code=int(status), media_type=media.decode("ascii"),
                        headers={"Cache-Control":"no-store", "X-FitMe-Job-State":"finished"})
    return pair_accepted(job)


def connection():
    return redis.Redis.from_url(settings.get("REDIS_URL", "redis://127.0.0.1:6380/0"),
                                socket_connect_timeout=2, socket_timeout=55)


def request(lane, operation, data):
    job = uuid.uuid4().hex
    key = f"{PREFIX}:job:{job}"
    stream = f"{PREFIX}:{lane}:requests"
    client = connection()
    try:
        # Keep bodies in expiring keys so an offline worker cannot retain photos.
        if client.xlen(stream) >= 100:
            raise HTTPException(503, "요청이 밀려 있어요. 잠시 후 다시 시도해 주세요.")
        if not client.exists(f"{PREFIX}:{lane}:online"):
            raise HTTPException(503, "처리 서버 연결을 기다리고 있어요. 잠시 후 다시 시도해 주세요.")
        with client.pipeline() as pipe:
            pipe.set(key, data, ex=TTL)
            pipe.xadd(stream, {"id": job, "op": operation})
            pipe.execute()
        if not client.blpop(key + ":ready", timeout=48 if lane == "media" else 18):
            raise HTTPException(504, "처리가 지연되고 있어요. 잠시 후 다시 시도해 주세요.")
        with client.pipeline() as pipe:
            pipe.hmget(key + ":result", "status", "media", "body")
            pipe.delete(key + ":result")
            (status, media, body), _ = pipe.execute()
        if not status or not media or body is None:
            raise HTTPException(503, "처리 결과를 받지 못했어요. 다시 시도해 주세요.")
        return Response(body, status_code=int(status), media_type=media.decode("ascii"),
                        headers={"Cache-Control": "no-store"})
    except redis.RedisError as exc:
        raise HTTPException(503, "요청을 전달할 수 없어요. 잠시 후 다시 시도해 주세요.") from exc
    finally:
        client.close()


def json_bytes(data):
    return json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
