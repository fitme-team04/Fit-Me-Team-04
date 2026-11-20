# 역할: Azure ML HTTPS·관리 ID/키 인증·입출력 계약·실패 처리와 B 방식 제거를 검사합니다.
import importlib
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from fastapi import HTTPException
import yaml

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'avatar/src'))
from core.features import SAM_MEASUREMENT_KEYS
from core.contract import PREDICTION_KEYS
from core.ml_endpoint import endpoint_settings, request_headers

ENDPOINT='https://fitme-test.koreacentral.inference.ml.azure.com/score'
FEATURES={'schema_version':2,'measurement_method':'sam_surface_sections_11_v2',
          'height_cm':175.,'weight_kg':70.,'sam_measurements':{key:40. for key in SAM_MEASUREMENT_KEYS}}


class EndpointTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.api=importlib.import_module('api.avatar')
        self.values={'male':{key:40. for key in PREDICTION_KEYS}}
        self.client=MagicMock()
        self.client.post=AsyncMock(return_value=httpx.Response(200,json=self.values,
            request=httpx.Request('POST',ENDPOINT)))
        self.context=MagicMock()
        self.context.__aenter__=AsyncMock(return_value=self.client)
        self.context.__aexit__=AsyncMock(return_value=False)

    async def test_example_mode_skips_endpoint_auth_and_http_and_scales_dimensions(self):
        with patch.dict(os.environ, {'FITME_PREDICTION_MODE':'example'}, clear=True), \
             patch.object(self.api, 'endpoint_settings') as settings, \
             patch.object(self.api, 'request_headers') as auth, \
             patch.object(self.api.httpx, 'AsyncClient') as client:
            base = await self.api.predict(FEATURES)
            taller = await self.api.predict(dict(FEATURES, height_cm=182.))
            settings.assert_not_called()
            auth.assert_not_called()
            client.assert_not_called()
        self.assertEqual(base['prediction_source'], 'example')
        self.assertEqual(base['male']['height_cm'], 175.)
        self.assertEqual(taller['male']['height_cm'], 182.)
        for key in PREDICTION_KEYS:
            self.assertGreater(base['male'][key], 0)
            self.assertAlmostEqual(taller['male'][key] / base['male'][key], 182 / 175)

    async def test_unknown_mode_fails_without_ml_or_silent_example_fallback(self):
        with patch.dict(os.environ, {'FITME_PREDICTION_MODE':'typo'}, clear=True), \
             patch.object(self.api.httpx, 'AsyncClient') as client:
            with self.assertRaises(HTTPException) as raised:
                await self.api.predict(FEATURES)
            self.assertEqual(raised.exception.status_code, 503)
            client.assert_not_called()

    async def test_key_auth_sends_13_features_and_restores_input_height(self):
        with patch.dict(os.environ,{'AZURE_ML_ENDPOINT':ENDPOINT,'AZURE_ML_AUTH':'key','AZURE_ML_KEY':'test-key',
                                  'ML_API_URL':'http://ml:8000/predict'},clear=True), \
             patch.object(self.api.httpx,'AsyncClient',return_value=self.context) as factory:
            result=await self.api.predict(FEATURES)
        self.client.post.assert_awaited_once_with(ENDPOINT,json=FEATURES,headers={'Authorization':'Bearer test-key'})
        factory.assert_called_once_with(timeout=90,trust_env=False,follow_redirects=False)
        self.assertEqual(result['male']['height_cm'],175.)
        self.assertEqual(result['male']['reference_pose'],'A')

    async def test_null_sam_field_reaches_ml_as_json_null(self):
        features = dict(FEATURES, sam_measurements=dict(FEATURES['sam_measurements'], knee_girth_cm=None))
        with patch.dict(os.environ, {'AZURE_ML_ENDPOINT':ENDPOINT, 'AZURE_ML_AUTH':'key', 'AZURE_ML_KEY':'test'}, clear=True), \
             patch.object(self.api.httpx, 'AsyncClient', return_value=self.context):
            await self.api.predict(features)
        self.assertIsNone(self.client.post.call_args.kwargs['json']['sam_measurements']['knee_girth_cm'])

    async def test_default_entra_auth_and_deployment_header(self):
        credential=MagicMock()
        credential.get_token.return_value=types.SimpleNamespace(token='test-entra-token')
        factory=MagicMock()
        factory.return_value.__enter__.return_value=credential
        with patch.dict(os.environ,{'AZURE_ML_ENDPOINT':ENDPOINT,'AZURE_ML_DEPLOYMENT':'measurements-v2'},clear=True), \
             patch('azure.identity.DefaultAzureCredential',factory), \
             patch.object(self.api.httpx,'AsyncClient',return_value=self.context):
            await self.api.predict(FEATURES)
        credential.get_token.assert_called_once_with('https://ml.azure.com/.default')
        self.assertEqual(self.client.post.call_args.kwargs['headers'],
            {'Authorization':'Bearer test-entra-token','azureml-model-deployment':'measurements-v2'})

    async def test_local_and_invalid_targets_fail_without_sending_credentials(self):
        for endpoint in ['', 'http://ml:8000/predict', ENDPOINT+'?token=bad',
                         'https://untrusted.example/score', ENDPOINT+'/bad']:
            with patch.dict(os.environ,{'AZURE_ML_ENDPOINT':endpoint},clear=True), \
                 patch.object(self.api,'request_headers') as auth:
                with self.assertRaises(HTTPException) as raised:
                    await self.api.predict(FEATURES)
                self.assertEqual(raised.exception.status_code,503)
                auth.assert_not_called()

    async def test_timeout_bad_output_and_token_failure_are_sanitized(self):
        with patch.dict(os.environ,{'AZURE_ML_ENDPOINT':ENDPOINT,'AZURE_ML_AUTH':'key','AZURE_ML_KEY':'test'},clear=True), \
             patch.object(self.api.httpx,'AsyncClient',return_value=self.context):
            self.client.post.side_effect=httpx.ReadTimeout('sensitive details')
            with self.assertRaises(HTTPException) as raised:
                await self.api.predict(FEATURES)
            self.assertEqual(raised.exception.status_code,504)
            self.client.post.side_effect=None
            self.client.post.return_value=httpx.Response(200,json={'male':{'height_cm':175}},request=httpx.Request('POST',ENDPOINT))
            with self.assertRaises(HTTPException) as raised:
                await self.api.predict(FEATURES)
            self.assertEqual(raised.exception.status_code,502)
        with patch.dict(os.environ,{'AZURE_ML_ENDPOINT':ENDPOINT},clear=True), \
             patch.object(self.api,'request_headers',side_effect=RuntimeError('secret')):
            with self.assertRaises(HTTPException) as raised:
                await self.api.predict(FEATURES)
            self.assertEqual(raised.exception.status_code,503)
            self.assertNotIn('secret',raised.exception.detail)


class DeploymentTests(unittest.TestCase):
    def test_only_avatar_and_sync_run_on_body_vm(self):
        services=yaml.safe_load((BASE/'avatar/compose.yaml').read_text(encoding='utf-8'))['services']
        self.assertEqual(set(services),{'avatar','model-sync'})
        self.assertFalse((BASE/'avatar/compose.ml.yaml').exists())
        self.assertFalse((BASE/'avatar/azureml/vm_api.py').exists())
        start=(BASE/'infra/deploy/body-start.sh').read_text(encoding='utf-8')
        self.assertNotIn('compose.ml.yaml',start)
        self.assertNotIn('ml-model/',start)

    def test_key_configuration_requires_secret_but_does_not_return_it(self):
        with self.assertRaises(ValueError):
            endpoint_settings({'AZURE_ML_ENDPOINT':ENDPOINT,'AZURE_ML_AUTH':'key'})
        self.assertEqual(endpoint_settings({'AZURE_ML_ENDPOINT':ENDPOINT}), (ENDPOINT,'aad_token',''))
