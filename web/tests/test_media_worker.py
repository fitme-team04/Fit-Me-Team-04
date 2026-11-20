"""Exercise VM -> worker -> capture ID -> Blob with a local VM/Blob fixture."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import struct
import sys
import threading
import unittest
from unittest.mock import patch

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import garment_measurement as gm
import v2_operations as worker


class GarmentMediaTests(unittest.TestCase):
    def test_vm_asset_replay_and_model(self):
        job = "1" * 32
        jpeg = b"\xff\xd8\xff\xdbtest\xff\xd9"
        result = {"basis":"garment","unit":"cm","category":"상의",
                  "measurements":{"chest_width":52},"model_blob":"models/one shirt.glb"}
        glb = (Path(gm.__file__).parent / "static/models/striped-tee.glb").read_bytes()
        saved, calls = {}, []

        class Service(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                calls.append((self.path, self.headers.get("Idempotency-Key"), self.rfile.read(int(self.headers["Content-Length"]))))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())

            def do_GET(self):
                calls.append(self.path)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(glb)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Service)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}"

        def save(key, data, name):
            saved[key] = {"result_json":json.dumps(data), "blob_name":name}

        try:
            with patch.dict(os.environ, {"GARMENT_MEASUREMENT_URL":url+"/vm",
                                         "GARMENT_BLOB_CONTAINER_URL":url+"/container?sp=r"}), \
                 patch.object(worker.v2_store, "save_capture", side_effect=save), \
                 patch.object(worker.v2_store, "capture", side_effect=saved.get):
                measured = worker.dispatch("media","measure",jpeg,job)
                self.assertEqual(measured["modelAsset"], job)
                self.assertNotIn("model_blob", measured)
                self.assertEqual(worker.dispatch("media","measure",jpeg,job), measured)
                imported = worker.dispatch("media","import",json.dumps(result).encode(),job)
                self.assertNotIn("modelAsset", imported)
                self.assertEqual(worker.dispatch("media","get_model",json.dumps({"id":job}).encode(),job), glb)
                self.assertEqual(calls, [("/vm",job,jpeg),"/container/models/one%20shirt.glb?sp=r"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_reject_external_paths_and_dependencies(self):
        for name in ["https://other.example/model.glb", "../model.glb", "sub/%2e%2e/model.glb", "/model.glb", "model.glb?sig=secret"]:
            with self.subTest(name=name), self.assertRaises(HTTPException):
                gm.validated_blob_name(name)
        with patch.dict(os.environ, {"GARMENT_BLOB_CONTAINER_URL":"https://untrusted.example/container?sp=r"}), self.assertRaises(HTTPException):
            gm.blob_url("model.glb")
        payload = b'{"asset":{"version":"2.0"},"images":[{"uri":"https://external/image"}]}'
        payload += b" " * (-len(payload) % 4)
        glb = struct.pack("<4sIII4s", b"glTF", 2, len(payload)+20, len(payload), b"JSON") + payload
        with self.assertRaises(HTTPException):
            gm.validate_glb(glb)


if __name__ == "__main__":
    unittest.main()
