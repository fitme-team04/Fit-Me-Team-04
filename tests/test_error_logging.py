# 역할: SAM 상주 프로세스 재사용·재시작과 비밀 없는 오류 로깅을 검사합니다.
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'avatar/src'))
from core.error_logging import register_error_logging


class LoggingTests(unittest.TestCase):
    def test_detail_and_validation_fields_are_logged_without_input_or_urls(self):
        app = FastAPI()
        register_error_logging(app)
        @app.get('/failure/{status}')
        def failure(status:int):
            raise HTTPException(status, 'model unavailable https://example.test/?sig=secret')
        @app.get('/validate')
        def validate(height:int):
            return height
        with self.assertLogs(level='WARNING') as captured:
            client=TestClient(app)
            self.assertEqual(client.get('/failure/422').status_code,422)
            self.assertEqual(client.get('/failure/503').status_code,503)
            self.assertEqual(client.get('/validate?height=private-input').status_code,422)
        logs='\n'.join(captured.output)
        self.assertIn('model unavailable',logs)
        self.assertIn('height',logs)
        self.assertNotIn('sig=secret',logs)
        self.assertNotIn('private-input',logs)
