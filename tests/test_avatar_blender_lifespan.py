# 역할: 신체 API가 SAM만 상주시키고 Blender는 시작·종료 때 실행하지 않는지 검사합니다.
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'avatar/src'))
from api import avatar


class AvatarLifespanTests(unittest.TestCase):
    def test_sam_only_starts_and_stops_once(self):
        with patch.object(avatar,'runtime_mode',return_value='resident'), \
             patch('subprocess.Popen') as blender, \
             patch.object(avatar.resident,'start') as sam_start,patch.object(avatar.resident,'stop') as sam_stop:
            with TestClient(avatar.app) as client:
                self.assertEqual(client.get('/health').status_code,200)
                blender.assert_not_called();sam_start.assert_called_once()
            blender.assert_not_called();sam_stop.assert_called_once()

    def test_sam_failure_does_not_start_blender(self):
        with patch.object(avatar,'runtime_mode',return_value='resident'), \
             patch('subprocess.Popen') as blender, \
             patch.object(avatar.resident,'start',side_effect=RuntimeError('unavailable')),patch.object(avatar.resident,'stop') as sam_stop:
            with self.assertRaises(RuntimeError):
                with TestClient(avatar.app):pass
            blender.assert_not_called();sam_stop.assert_called_once()


if __name__=='__main__':unittest.main()
