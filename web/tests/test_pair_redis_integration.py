"""Exercise the authenticated gateway, Redis, team VM contracts, and file-scoped downloads."""
import base64
import hashlib
import json
import os
import struct
import threading
import time
import unittest
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from urllib.request import urlopen
from uuid import uuid4

from fastapi.testclient import TestClient

import main
from test_model_pair import BODY, PNG, SELECTION, receipt
import v2_bus


def synthetic_glb(side):
    chunk = json.dumps({"asset":{"version":"2.0","generator":"fixture-" + side}}).encode()
    chunk += b" " * (-len(chunk) % 4)
    return struct.pack("<4sIII4s", b"glTF", 2, 20 + len(chunk), len(chunk), b"JSON") + chunk


@unittest.skipUnless(os.environ.get("V2_INTEGRATION_REDIS_URL"), "Set V2_INTEGRATION_REDIS_URL to use real Redis")
class ModelExchangeTests(unittest.TestCase):
    def test_authenticated_generation_replay_and_direct_download(self):
        # Production images run on independent hosts; neither needs access to the frontend.
        barrier = threading.Barrier(2, timeout=6)
        allow_finish = threading.Event()
        received, stored, downloaded = {}, {}, []

        def fake_vm(side):
            class Service(BaseHTTPRequestHandler):
                def log_message(self, *_args):
                    pass

                def reply(self, data, media):
                    self.send_response(200)
                    self.send_header("Content-Type", media)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)

                def do_POST(self):
                    received.setdefault(side, []).append(
                        (self.path, dict(self.headers.items()), self.rfile.read(int(self.headers["Content-Length"]))))
                    barrier.wait()
                    allow_finish.wait(timeout=6)
                    glb = synthetic_glb(side)
                    model_id = hashlib.sha256(glb).hexdigest()
                    url_root = f"http://127.0.0.1:{self.server.server_port}"
                    response = receipt(url_root + "/blobs", side, model_id, self.headers["X-FitMe-Subject"])
                    metadata = json.dumps({"schema_version":1,"model_sha256":model_id}).encode()
                    for filename, url in response["urls"].items():
                        stored[url.removeprefix(url_root)] = glb if filename == "model.glb" else metadata
                    self.reply(json.dumps(response).encode(), "application/json")

                def do_GET(self):
                    downloaded.append(self.path)
                    self.reply(stored[self.path], "application/json" if self.path.endswith(".json") else "model/gltf-binary")
            return Service

        with ExitStack() as cleanup:
            config = {"V2_EMBEDDED_WORKERS":"true", "REDIS_URL":os.environ["V2_INTEGRATION_REDIS_URL"],
                      "V2_MODEL_INGRESS_TOKEN":uuid4().hex}
            for side, route in [("body","avatars"), ("garment","garments")]:
                service = ThreadingHTTPServer(("127.0.0.1", 0), fake_vm(side))
                threading.Thread(target=service.serve_forever, daemon=True).start()
                cleanup.callback(service.server_close)
                cleanup.callback(service.shutdown)
                base = f"http://127.0.0.1:{service.server_port}"
                config[side.upper() + "_MODEL_VM_URL"] = base + "/api/" + route
                config[side.upper() + "_MODEL_BLOB_BASE"] = base + "/blobs"
            cleanup.enter_context(patch.dict(os.environ, config))
            prefix = "fitme:test:" + uuid4().hex
            cleanup.enter_context(patch("v2_bus.PREFIX", prefix))
            cleanup.enter_context(patch("v2_worker.PREFIX", prefix))
            cache = cleanup.enter_context(v2_bus.connection())
            def clean_keys():
                for key in cache.scan_iter(match=prefix + ":*"):
                    cache.delete(key)
            cleanup.callback(clean_keys)
            web = cleanup.enter_context(TestClient(main.app))
            cleanup.callback(allow_finish.set)
            deadline = time.monotonic() + 5
            while not all(cache.exists(f"{prefix}:{lane}:online") for lane in ("pair", "media")):
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.02)

            create = "/api/v2/model-pair"
            owner = {"X-FitMe-Ingress-Token": config["V2_MODEL_INGRESS_TOKEN"], "X-FitMe-Subject":"signed-in-test"}
            retry = {**owner, "Idempotency-Key":uuid4().hex}
            other = dict(owner, **{"X-FitMe-Subject":"other-user"})
            payload = {"body":BODY, "garment":SELECTION}
            self.assertTrue(web.get(create+"/status", headers=owner).json()["authenticated"])
            self.assertFalse(web.get(create+"/status", headers={"X-FitMe-Subject":"spoof"}).json()["authenticated"])
            self.assertEqual(web.post(create,json=payload,headers={"X-FitMe-Subject":"spoof"}).status_code,401)
            invalid = dict(payload, body=dict(BODY, photo_mime="image/jpeg"))
            rejected = web.post(create,json=invalid,headers=retry)
            self.assertEqual(rejected.status_code,422)
            self.assertNotIn(PNG, rejected.text)
            start = web.post(create, json=payload, headers=retry)
            self.assertEqual(start.status_code,202, start.text)
            poll = start.json()["status_url"]
            self.assertEqual(web.get(poll,headers=owner).status_code,202)
            self.assertEqual(web.get(poll,headers=other).status_code,404)
            self.assertEqual(web.post(create,json=payload,headers=retry).json()["status_url"], poll)
            conflict = dict(payload, body=dict(BODY,weight_kg=75))
            self.assertEqual(web.post(create,json=conflict,headers=retry).status_code,409)
            allow_finish.set()
            deadline = time.monotonic() + 10
            while (response := web.get(poll, headers=owner)).status_code == 202:
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.03)
            self.assertEqual(response.status_code,200, response.text)
            models = response.json()
            self.assertEqual([len(received[side]) for side in ("body","garment")], [1,1])
            self.assertEqual(received["body"][0][0],"/api/avatars")
            self.assertEqual(received["body"][0][2],base64.b64decode(PNG))
            self.assertEqual(received["garment"][0][0],"/api/garments")
            self.assertEqual(json.loads(received["garment"][0][2]),SELECTION)
            for side in ("body","garment"):
                self.assertNotIn(config["V2_MODEL_INGRESS_TOKEN"],received[side][0][1].values())
            self.assertEqual(downloaded, [])
            for side in ("body","garment"):
                result = models[side]
                self.assertEqual(result["status"],"ready",result)
                with urlopen(result["glb_url"], timeout=3) as file:
                    digest = hashlib.sha256(file.read()).hexdigest()
                self.assertEqual(digest,result["model_id"])
                with urlopen(result["anchors_url"], timeout=3) as file:
                    self.assertEqual(json.load(file)["model_sha256"],digest)
            self.assertEqual(len(downloaded),4)
            self.assertEqual(web.get(poll,headers=owner).json(),models)
            self.assertEqual(web.get(poll,headers=other).status_code,404)
            self.assertEqual(web.get(poll,headers={"X-FitMe-Subject":"signed-in-test"}).status_code,401)
