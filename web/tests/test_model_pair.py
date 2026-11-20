"""The model worker adapts V2 data to the team's two different VM wire contracts."""
import base64
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from io import BytesIO
import os
from pathlib import Path
import sys
import threading
import importlib.util
from types import ModuleType
import unittest
from unittest.mock import patch, MagicMock
from urllib.parse import urlencode
from urllib.error import HTTPError
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import model_pair


PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgZGIGAAAOAAfXb+R4AAAAAElFTkSuQmCC"
BODY = {"height_cm":170, "weight_kg":65, "photo_b64":PNG, "photo_mime":"image/png"}
SELECTION = {"garment_id":16, "size_id":83}


def receipt(base, side, digest, subject):
    kind = "avatars/" + sha256(subject.encode()).hexdigest() if side == "body" else "garments"
    prefix = f"{base}/v2/{kind}/{digest}/"
    names = ["model.glb", "anchors.json"]
    if side == "body":
        names.append("measurements.json")
    return {"status":"ready", "model_id":digest, "urls":{name:prefix + name for name in names}}


class PairTests(unittest.TestCase):
    def test_known_photo_rejection_reaches_web_without_upstream_exception_text(self):
        body=model_pair.BodyInput.model_validate(BODY)
        for code in ('full_body_required','single_person_required','unknown_private_error'):
            with self.subTest(code=code):
                failure=HTTPError('http://localhost/api/avatars',422,'Unprocessable Entity',{},
                    BytesIO(json.dumps({'detail':{'code':code,'message':'private server text'}}).encode()))
                with patch.object(model_pair,'build_opener') as opener:
                    opener.return_value.open.side_effect=failure
                    result=model_pair.generate('body',body,('http://localhost/api/avatars',None),'owner')
                self.assertEqual(result['status'],'error')
                self.assertNotIn('private server text',result['message'])
                self.assertEqual(result.get('error_code'),None if code.startswith('unknown') else code)

    def test_rejected_photo_never_starts_garment_generation(self):
        request=model_pair.ModelPairRequest.model_validate({'body':BODY,'garment':SELECTION})
        with patch.object(model_pair,'configuration',return_value={'body':('body',None),'garment':('garment',None)}), \
             patch.object(model_pair,'generate',return_value={'status':'error','error_code':'full_body_required','message':'다시 촬영'}) as generate:
            result=model_pair.generate_pair(request,'owner')
        generate.assert_called_once()
        self.assertEqual(generate.call_args.args[0],'body')
        self.assertEqual(result['body']['error_code'],'full_body_required')
        self.assertEqual(result['garment']['status'],'error')

    def test_malformed_photo_error_still_returns_a_safe_failure(self):
        body=model_pair.BodyInput.model_validate(BODY)
        for data in (b'[]',b'['*1500+b'0'+b']'*1500,b'x'*5000):
            failure=HTTPError('http://localhost/api/avatars',422,'Unprocessable Entity',{},BytesIO(data))
            with patch.object(model_pair,'build_opener') as opener:
                opener.return_value.open.side_effect=failure
                result=model_pair.generate('body',body,('http://localhost/api/avatars',None),'owner')
            self.assertEqual(result,{'status':'error','message':'한 사람의 전신이 보이는 JPEG·PNG 사진과 입력값을 확인해 주세요.'})

    def test_truncated_photo_error_does_not_escape_as_a_web_server_error(self):
        failure=HTTPError('http://localhost/api/avatars',422,'Unprocessable Entity',{},BytesIO())
        with patch.object(failure,'read',side_effect=model_pair.HTTPProtocolError('truncated')), \
             patch.object(model_pair,'build_opener') as opener:
            opener.return_value.open.side_effect=failure
            result=model_pair.generate('body',model_pair.BodyInput.model_validate(BODY),('http://localhost/api/avatars',None),'owner')
        self.assertEqual(result['status'],'error')
        self.assertNotIn('truncated',result['message'])

    def test_failed_preview_retains_error_status_and_validated_assets(self):
        base_url = 'http://localhost/blob/garment'
        base = model_pair.blob_base(base_url)
        value = receipt(base_url, 'garment', 'a'*64, 'owner')
        value.update(status='error', preview_available=True,
                     failure_reasons=['stretch_exceeded','body_penetration'])
        result = model_pair.ready_model('garment', value, base, 'owner')
        self.assertEqual(result['status'], 'error')
        self.assertTrue(result['preview_available'])
        self.assertEqual(result['failure_reasons'], value['failure_reasons'])
        timeout={**value,'failure_reasons':['simulation_incomplete','simulation_timeout']}
        self.assertEqual(model_pair.ready_model('garment',timeout,base,'owner')['status'],'error')
        for reason in ('frame_timeout','pushout_rejected','collision_region_exited',
                       'compression_exceeded','invalid_rest_mesh','invalid_cloth_mesh','validation_incomplete',
                       'self_collision_setup_failed','sam_sizing_failed'):
            failure={**value,'failure_reasons':[reason]}
            self.assertTrue(model_pair.ready_model('garment',failure,base,'owner')['preview_available'])
        self.assertTrue(result['glb_url'].endswith('/model.glb'))
        with self.assertRaises(ValueError):
            model_pair.ready_model('garment', {**value, 'preview_available':False}, base, 'owner')
        invalid = {**value, 'urls':{**value['urls'], 'model.glb':'http://localhost/other/model.glb'}}
        with self.assertRaises(ValueError):
            model_pair.ready_model('garment', invalid, base, 'owner')
        with self.assertRaises(ValueError):
            model_pair.ready_model('body', value, base, 'owner')

    def test_sam_garment_request_uses_catalog_template_without_db_measurements(self):
        from fastapi import APIRouter
        root = Path(__file__).resolve().parents[2]/'garment/src'
        replacements = {}
        for name in ('core.runtime', 'geometry.template_catalog', 'database.connection', 'storage.blob_assets'):
            replacements[name] = ModuleType(name)
        render = replacements['core.runtime'].render = MagicMock(return_value={'status':'ready'})
        replacements['database.connection'].DatabaseUnavailable = type('DatabaseUnavailable',(RuntimeError,),{})
        replacements['geometry.template_catalog'].resolve_template = MagicMock(return_value={'sleeve_basis':'center_back'})
        rows = [dict(garment_id=16, item_code='sample', category='상의', source_name='sample',
                     region='KR', size_label='M', measure_code=key, value_cm=value)
                for key,value in {'body_length':69., 'garment_shoulder_width':46.5,
                                  'chest_width':53., 'sleeve_length':22.}.items()]
        query = replacements['database.connection'].query = MagicMock(
            side_effect=[rows, [{'alias_name':'sleeve-length'}]])
        replacements['storage.blob_assets'].principal = lambda: 'owner'
        replacements['storage.blob_assets'].downloads = lambda _: APIRouter()
        sys.path.insert(0, str(root))
        try:
            with patch.dict(sys.modules, replacements):
                spec = importlib.util.spec_from_file_location('garment_api_cloth_test', root/'api/garments.py')
                api = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(api)
                choice = api.Selection(garment_id=16, size_id=83, body_model_id='a'*64)
                api.garment(choice, subject='owner')
                payload = render.call_args.args[0]
                self.assertEqual(payload['spec'], {})
                self.assertEqual(payload['geometry_mode'], 'sam_body')
                self.assertEqual(payload['body_model_id'], 'a'*64)
                query.assert_called_once()
                self.assertNotIn('garment.measures', query.call_args_list[0].args[0])
                with self.assertRaises(ValidationError):
                    api.Selection(garment_id=16, size_id=83, body_measurements={'chest_width_cm':100})
        finally:
            sys.path.remove(str(root))

    def test_body_first_then_db_cloth_garment_and_one_failed_receipt(self):
        subject = "example-signed-in-owner"
        listing_id = uuid4().hex
        seen = {}
        break_garment = False

        class VM(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_POST(self):
                side = {"/api/avatars":"body", "/api/garments":"garment"}[self.path]
                incoming = self.rfile.read(int(self.headers["Content-Length"]))
                seen[side] = (incoming, dict((k.lower(), v) for k, v in self.headers.items()))
                if side == 'garment':
                    assert 'body' in seen
                digest = sha256(side.encode()).hexdigest()
                value = receipt(f"{origin}/blob/{side}", side, digest, subject)
                if break_garment and side == "garment":
                    value["urls"]["anchors.json"] = value["urls"]["model.glb"]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(value).encode())

        server = ThreadingHTTPServer(("127.0.0.1", 0), VM)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f"http://127.0.0.1:{server.server_port}"
        config = {"BODY_MODEL_VM_URL":origin+"/api/avatars", "GARMENT_MODEL_VM_URL":origin+"/api/garments",
                  "BODY_MODEL_BLOB_BASE":origin+"/blob/body", "GARMENT_MODEL_BLOB_BASE":origin+"/blob/garment"}
        request = model_pair.ModelPairRequest.model_validate({"body":BODY,"garment":{"listing_id":listing_id}})
        saved = {"name":"private note", "rows":[["가슴단면",51,"직접 실측"]], "catalogSelection":SELECTION}
        try:
            with patch.dict(os.environ, config), patch("v2_store.get_listing", return_value=saved) as read_listing:
                result = model_pair.generate_pair(request, subject)
                read_listing.assert_called_once_with(listing_id)
                self.assertEqual(seen["body"][0], base64.b64decode(PNG))
                self.assertEqual(seen["body"][1]["content-type"], "image/png")
                self.assertEqual(float(seen["body"][1]["height-cm"]), 170)
                self.assertEqual(float(seen["body"][1]["weight-kg"]), 65)
                payload = json.loads(seen["garment"][0])
                self.assertEqual(payload, {**SELECTION, 'body_model_id':sha256(b'body').hexdigest()})
                self.assertNotIn('body_measurements', payload)
                self.assertNotIn("height-cm",seen["garment"][1])
                for side in seen:
                    self.assertEqual(seen[side][1]["x-fitme-subject"], subject)
                    self.assertEqual(result[side]["status"], "ready")
                    self.assertTrue(result[side]["anchors_url"].endswith("/anchors.json"))
                self.assertTrue(result["body"]["measurements_url"].endswith("/measurements.json"))
                self.assertNotIn("measurements_url",result["garment"])
                barrier = threading.Barrier(1, timeout=4)  # 의류만 요청하면 VM 호출이 한 번뿐이다
                garment_only = model_pair.generate_pair(model_pair.ModelPairRequest.model_validate(
                    {"garment":{"listing_id":listing_id}}), subject)
                self.assertEqual(set(garment_only), {"garment"})
                self.assertEqual(garment_only["garment"]["status"], "ready")
                barrier = threading.Barrier(2, timeout=4)
                break_garment = True
                partial = model_pair.generate_pair(request, subject)
                self.assertEqual(partial["body"]["status"], "ready")
                self.assertEqual(partial["garment"]["status"], "error")
                self.assertNotIn("glb_url", partial["garment"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_body_failure_does_not_request_garment(self):
        request = model_pair.ModelPairRequest.model_validate({'body':BODY, 'garment':SELECTION})
        with patch.object(model_pair, 'configuration', return_value={'body':('vm','base')}), \
                patch.object(model_pair, 'generate', return_value={'status':'error'}) as generate:
            result = model_pair.generate_pair(request, 'owner')
        self.assertEqual(generate.call_count, 1)
        self.assertEqual(generate.call_args.args[0], 'body')
        self.assertEqual(result['garment']['status'], 'error')

    def test_garment_only_request_drapes_on_existing_body(self):
        request = model_pair.ModelPairRequest.model_validate(
            {'garment':SELECTION, 'body_model_id':'b' * 64})
        with patch.object(model_pair, 'configuration', return_value={'garment':('vm','base')}), \
                patch.object(model_pair, 'generate', return_value={'status':'ready'}) as generate:
            result = model_pair.generate_pair(request, 'owner')
        self.assertEqual(set(result), {'garment'})
        self.assertEqual(generate.call_count, 1)
        self.assertEqual(generate.call_args.args[0], 'garment')
        self.assertEqual(generate.call_args.args[1]['body_model_id'], 'b' * 64)
        with self.assertRaises(ValidationError):
            model_pair.ModelPairRequest.model_validate({'garment':SELECTION, 'body_model_id':'not-a-digest'})

    def test_blob_links_bound_to_owner_model_digest_and_file(self):
        url_base = "https://fitmodels.blob.core.windows.net/body"
        base = model_pair.blob_base(url_base)
        digest, owner = "a" * 64, "buyer-1"
        value = receipt(url_base, "body", digest, owner)
        expiry = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        sas = "?" + urlencode({"sr":"b","sp":"r","se":expiry,"sig":"fixture"})
        value["urls"] = {file:url+sas for file,url in value["urls"].items()}
        result = model_pair.ready_model("body",value,base,owner)
        url = value["urls"]["model.glb"]
        self.assertEqual(result["glb_url"],url)
        sha_owner = sha256(owner.encode()).hexdigest()
        for bad in [url.replace(sha_owner, "b"*64),url.replace(digest,"b"*64),url.replace("model.glb","anchors.json"),
                    url.replace("fitmodels.","untrusted."),url.replace("/body/","/body-other/"),
                    url.replace("/model.glb","/%2e%2e/model.glb"),url.replace("sp=r","sp=rw"),
                    url.replace("sr=b","sr=c"), url.split("?")[0]]:
            changed = dict(value, urls=dict(value["urls"], **{"model.glb":bad}))
            with self.subTest(url=bad), self.assertRaises(ValueError):
                model_pair.ready_model("body", changed, base, owner)
        for bad in [dict(value,status="pending"),dict(value,model_id=digest.upper()),dict(value,urls={})]:
            with self.assertRaises(ValueError):
                model_pair.ready_model("body",bad,base,owner)

    def test_inputs_allow_only_real_catalog_ids_and_bounded_photo(self):
        payload = {"body":BODY,"garment":SELECTION}
        self.assertEqual(model_pair.ModelPairRequest.model_validate(payload).garment.garment_id, SELECTION["garment_id"])
        for body in [dict(BODY,photo_b64="abcd"),dict(BODY,photo_b64="!!!!"),
                     dict(BODY,photo_mime="image/jpeg"),dict(BODY,photo_b64=PNG+"A"*model_pair.MAX_PHOTO_B64),
                     dict(BODY,subject="not-from-gateway")]:
            with self.assertRaises(ValidationError):
                model_pair.ModelPairRequest.model_validate(dict(payload,body=body))
        for invalid in [dict(SELECTION, listing_id=uuid4().hex), dict(SELECTION, size_id=True),
                        {"category":"상의·아우터","rows":[["가슴단면",54,"직접 실측"]]}, {"listing_id":"bad"}]:
            with self.assertRaises(ValidationError):
                model_pair.ModelPairRequest.model_validate(dict(payload,garment=invalid))
        ref = model_pair.ListingReference(listing_id=uuid4().hex)
        with patch("v2_store.get_listing", return_value={"rows":[["가슴단면",51,"직접 실측"]]}):
            with self.assertRaises(HTTPException) as failure:
                model_pair.garment_selection(ref)
            self.assertEqual(failure.exception.status_code,422)


if __name__ == "__main__":
    unittest.main()


class FitJudgeTests(unittest.TestCase):
    """신체 결과 → 의류 서버 /fit. 판정 기준은 /fit(ease_check)에만 있다."""

    def serve(self, fit_reply=None, fit_status=200, measurements=None):
        seen = {"fit":[]}

        class Server(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_GET(self):
                body = json.dumps(measurements if measurements is not None else {"measurements":{
                    "chest_girth_cm":{"target":98.0, "measured":97.6}, "waist_girth_cm":{"target":82.0},
                    "hip_girth_cm":95.5, "chest_width_cm":{"target":35.0}}}).encode()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                seen["fit"].append((json.loads(self.rfile.read(int(self.headers["Content-Length"]))), self.path,
                                    self.headers["X-FitMe-Subject"]))
                self.send_response(fit_status)
                self.end_headers()
                self.wfile.write(json.dumps(fit_reply or {}).encode())

        server = ThreadingHTTPServer(("127.0.0.1", 0), Server)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close(), thread.join()))
        return f"http://127.0.0.1:{server.server_port}", seen

    def body(self, origin):
        return {"status":"ready", "model_id":"a" * 64, "measurements_url":origin + "/blob/measurements.json"}

    def test_sends_item_size_and_three_girths_and_keeps_message(self):
        reply = {"selected":{"verdict":"NO_FIT", "message_ko":"맞지 않습니다. 가슴둘레 여유 +1.0cm로 작습니다 (기준 3cm 미만)",
                             "parts":[{"part":"chest_girth_cm", "status":"TOO_TIGHT", "ease_cm":1.0}]},
                 "recommended_size":"L", "all_sizes":[{"size_label":"M", "verdict":"NO_FIT"}, {"size_label":"L", "verdict":"FIT"}],
                 "rules_version":"ease-2026-11-16.v3"}
        origin, seen = self.serve(reply)
        target = model_pair.FitTarget(item_code="E422992-000", size_label="M")
        with patch.dict(os.environ, {"GARMENT_MODEL_VM_URL":origin + "/api/garments", "GARMENT_FIT_URL":""}):
            result = model_pair.judge_fit(target, self.body(origin), "buyer-1")
        sent, path, subject = seen["fit"][0]
        self.assertEqual(path, "/fit")
        self.assertEqual(subject, "buyer-1")
        self.assertEqual(sent, {"item_code":"E422992-000", "size_label":"M",
                                "chest_girth_cm":98.0, "waist_girth_cm":82.0, "hip_girth_cm":95.5})
        self.assertEqual(result["selected"]["message_ko"], reply["selected"]["message_ko"])
        self.assertEqual(result["selected"]["verdict"], "NO_FIT")
        self.assertEqual(result["selected"]["parts"], [{"part":"chest_girth_cm", "status":"TOO_TIGHT"}])
        self.assertEqual(result["recommended_size"], "L")
        self.assertEqual(result["all_sizes"][1], {"size_label":"L", "verdict":"FIT"})

    def test_sam_measured_girths_are_used_when_ml_target_is_empty(self):
        sam_only = {"measurements":{"chest_girth_cm":{"target":None, "measured":96.4},
                                    "waist_girth_cm":{"target":None, "measured":80.2},
                                    "hip_girth_cm":{"target":None, "measured":101.0}}}
        origin, seen = self.serve({"selected":{"verdict":"FIT", "message_ko":"입을 수 있습니다."}}, measurements=sam_only)
        target = model_pair.FitTarget(item_code="E422992-000", size_label="M")
        with patch.dict(os.environ, {"GARMENT_MODEL_VM_URL":origin + "/api/garments", "GARMENT_FIT_URL":""}):
            model_pair.judge_fit(target, self.body(origin), "buyer-1")
        self.assertEqual(seen["fit"][0][0], {"item_code":"E422992-000", "size_label":"M",
                                             "chest_girth_cm":96.4, "waist_girth_cm":80.2, "hip_girth_cm":101.0})

    def test_failed_body_skips_fit_and_is_undetermined(self):
        origin, seen = self.serve({"selected":{"verdict":"FIT", "message_ko":"입을 수 있습니다."}})
        target = model_pair.FitTarget(item_code="E422992-000", size_label="M")
        with patch.dict(os.environ, {"GARMENT_MODEL_VM_URL":origin + "/api/garments"}):
            result = model_pair.judge_fit(target, {"status":"error", "message":"x"}, "buyer-1")
        self.assertEqual(seen["fit"], [])
        self.assertEqual(result["selected"]["verdict"], "UNDETERMINED")
        self.assertTrue(result["selected"]["message_ko"].startswith("판정할 수 없습니다"))

    def test_fit_failure_leaves_out_only_the_verdict(self):
        origin, _seen = self.serve({"detail":"boom"}, fit_status=500)
        target = model_pair.FitTarget(item_code="E422992-000", size_label="M")
        with patch.dict(os.environ, {"GARMENT_MODEL_VM_URL":origin + "/api/garments"}):
            self.assertIsNone(model_pair.judge_fit(target, self.body(origin), "buyer-1"))
        origin, _seen = self.serve({"selected":{"verdict":"MAYBE", "message_ko":"?"}})
        with patch.dict(os.environ, {"GARMENT_MODEL_VM_URL":origin + "/api/garments"}):
            self.assertIsNone(model_pair.judge_fit(target, self.body(origin), "buyer-1"))

    def test_fit_target_rejects_odd_item_codes(self):
        with self.assertRaises(ValidationError):
            model_pair.FitTarget(item_code="../etc", size_label="M")
