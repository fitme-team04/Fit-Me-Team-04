# 역할: 배포 경로·인증·모델 다운로드 동작을 오프라인으로 검사합니다.
"""Offline regression checks for model integrity and ODBC authentication."""
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.models = load('blob_models', 'avatar/scripts/download_blob_models.py')
        self.payload = b'verified model bytes'
        self.meta = {'bytes': len(self.payload), 'sha256': hashlib.sha256(self.payload).hexdigest()}

    def transfer(self, destination, payload, failure=False):
        class Blob:
            def get_blob_properties(inner):
                return types.SimpleNamespace(size=self.meta['bytes'], etag='pinned-etag')

            def download_blob(inner, **kwargs):
                self.assertEqual(kwargs['etag'], 'pinned-etag')

                def readinto(stream):
                    stream.write(payload)
                    if failure:
                        raise OSError('interrupted')
                return types.SimpleNamespace(readinto=readinto)

        container = types.SimpleNamespace(get_blob_client=lambda name: Blob())
        core = types.ModuleType('azure.core')
        core.MatchConditions = types.SimpleNamespace(IfNotModified='unchanged')
        with patch.dict(sys.modules, {'azure.core': core}):
            self.models.download_one(container, 'mhr_model.pt', destination, self.meta)

    def test_verified_download_and_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'model.pt'
            self.transfer(target, self.payload)
            self.assertTrue(self.models.valid_file(target, self.meta))
            self.models.download_one(None, 'mhr_model.pt', target, self.meta)
            self.assertEqual(list(Path(tmp).iterdir()), [target])

    def test_corrupt_download_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'model.pt'
            target.write_bytes(b'previous model')
            with self.assertRaises(ValueError):
                self.transfer(target, b'x' * len(self.payload))
            self.assertEqual(target.read_bytes(), b'previous model')
            self.assertEqual(list(Path(tmp).iterdir()), [target])

    def test_interrupted_download_cleans_temporary_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'model.pt'
            with self.assertRaises(OSError):
                self.transfer(target, b'partial', failure=True)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_missing_and_wrong_size_are_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'model.pt'
            self.assertFalse(self.models.valid_file(target, self.meta))
            target.write_bytes(b'partial')
            self.assertFalse(self.models.valid_file(target, self.meta))

    def test_default_model_set_includes_all_four_assets(self):
        records = {name: self.meta for name in (
            'mhr_model.pt', 'fitme_depth_fixed.blend', 'a_pose.npz', 'sam_body.npz')}
        self.assertEqual(set(self.models.selected_models(records)), set(records))
        del records['sam_body.npz']
        with self.assertRaises(ValueError):
            self.models.selected_models(records)

    def test_main_downloads_complete_set_and_reuses_verified_cache_offline(self):
        records = {name: self.meta for name in self.models.MODEL_FILES}
        service = MagicMock()
        container = service.get_container_client.return_value
        blob = container.get_blob_client.return_value
        blob.get_blob_properties.return_value = types.SimpleNamespace(size=len(self.payload), etag='version')
        blob.download_blob.return_value.readinto.side_effect = lambda stream: stream.write(self.payload)
        sdk = types.ModuleType('azure.storage.blob')
        sdk.BlobServiceClient = MagicMock()
        sdk.BlobServiceClient.from_connection_string.return_value.__enter__.return_value = service
        identity = types.ModuleType('azure.identity')
        identity.DefaultAzureCredential = MagicMock()
        core = types.ModuleType('azure.core')
        core.MatchConditions = types.SimpleNamespace(IfNotModified='unchanged')
        modules = {'azure.storage.blob': sdk, 'azure.identity': identity, 'azure.core': core}
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(sys, 'argv', ['download_blob_models.py', '--models', tmp]), \
                patch.object(self.models.json, 'loads', return_value={'files': records}), \
                patch.dict('os.environ', {'AZURE_MODELS_CONNECTION_STRING': 'test-only'}, clear=True):
            with patch.dict(sys.modules, modules):
                self.models.main()
            self.assertEqual({p.name for p in Path(tmp).iterdir()}, set(records))
            self.assertEqual(container.get_blob_client.call_count, 4)
            # Cache path must work without Azure SDK imports or authentication.
            with patch.dict(sys.modules, {name: None for name in modules}):
                self.models.main()

    def test_odbc_authentication_in_all_deployments(self):
        for path in ['garment/src/database/connection.py']:
            with self.subTest(path=path), patch.dict(sys.modules, {'pyodbc': types.ModuleType('pyodbc')}):
                database = load('database_under_test', path)
                env = {'AZURE_SQL_SERVER': 'example.database.windows.net', 'AZURE_SQL_DATABASE': 'fitme',
                       'AZURE_SQL_AUTHENTICATION': 'ActiveDirectoryMsi', 'AZURE_SQL_PASSWORD': 'unused'}
                with patch.dict('os.environ', env, clear=True):
                    value = database.connection_string()
                    self.assertIn('Authentication={ActiveDirectoryMsi}', value)
                    self.assertNotIn('PWD=', value)
                    self.assertIn('TrustServerCertificate={no}', value)
                env.update(AZURE_SQL_AUTHENTICATION='SqlPassword', AZURE_SQL_USERNAME='user',
                           AZURE_SQL_PASSWORD='a};b')
                with patch.dict('os.environ', env, clear=True):
                    self.assertIn('PWD={a}};b}', database.connection_string())
                with patch.dict('os.environ', {'AZURE_SQL_CONNECTION_STRING': 'explicit'}, clear=True):
                    self.assertEqual(database.connection_string(), 'explicit')
                with patch.dict('os.environ', {'AZURE_SQL_AUTHENTICATION': 'invalid'}, clear=True):
                    with self.assertRaises(ValueError):
                        database.connection_string()


if __name__ == '__main__':
    unittest.main()
