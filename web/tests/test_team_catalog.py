import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

import team_catalog
from v2_store import Listing


class TeamCatalogTests(unittest.TestCase):
    def test_vm_ids_and_size_membership(self):
        calls = []

        class Service(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_GET(self):
                calls.append(self.path)
                # Deliberately use IDs that differ from V2's locally seeded MySQL catalog.
                rows = {
                    "/api/garments": [{"garment_id":831, "item_code":"QA-1", "garment_name":"테스트 옷"}],
                    "/api/garments/831/sizes": [{"size_id":912, "size_label":"M", "region":"KR"}],
                    "/api/garments/832/sizes": [],
                }[self.path]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(rows).encode())

        with ThreadingHTTPServer(("127.0.0.1", 0), Service) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/api/garments"
                with patch.dict(os.environ, {"GARMENT_MODEL_VM_URL":url}):
                    self.assertEqual(team_catalog.list_garments()["items"][0]["garment_id"], 831)
                    self.assertEqual(team_catalog.check_selection(831,912), {"ok":True})
                    for garment, size in [(831,17), (832,912), (True,912), (831,False)]:
                        with self.assertRaises(HTTPException) as failure:
                            team_catalog.check_selection(garment,size)
                        self.assertEqual(failure.exception.status_code,422)
                self.assertEqual(calls, ["/api/garments", "/api/garments/831/sizes", "/api/garments/831/sizes",
                                         "/api/garments/832/sizes"])
            finally:
                server.shutdown()
                thread.join()

    def test_mapping_is_optional_and_independent_of_used_garment_dimensions(self):
        legacy = dict(v=1,name="수선한 티셔츠",category="상의·아우터",size="M",note="",
                      rows=[["가슴단면",48,"직접 실측"]])
        self.assertNotIn("catalogSelection",Listing.model_validate(legacy).model_dump(exclude_none=True))
        selected = Listing.model_validate(dict(legacy,catalogSelection={"garment_id":831,"size_id":912}))
        self.assertEqual(selected.model_dump(mode="json")["rows"],legacy["rows"])
        for invalid in ({"garment_id":"831","size_id":912}, {"garment_id":0,"size_id":912},
                        {"garment_id":831,"size_id":912,"glb_url":"x"}):
            with self.assertRaises(ValidationError):
                Listing.model_validate(dict(legacy,catalogSelection=invalid))
