# 역할: memfd 미지원 환경의 Blender 출력·임시 파일 정리를 검사합니다.
from io import BytesIO
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from PIL import Image
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'avatar/src'))
from core import runtime


class RuntimeTests(unittest.TestCase):
    def test_memfd_and_shm_fallback_publish_and_close_descriptor(self):
        temporary_file = tempfile.TemporaryFile
        glb = b'glTF' + (2).to_bytes(4, 'little') + (12).to_bytes(4, 'little')
        for mode in ('available', 'absent', 'unsupported'):
            with self.subTest(mode=mode), temporary_file() as backing:
                created = []
                def fallback(**kwargs):
                    self.assertEqual(kwargs, {'mode':'w+b', 'dir':'/dev/shm'})
                    return temporary_file()
                def blender(*args, **kwargs):
                    fd = kwargs['pass_fds'][0]
                    self.assertEqual(kwargs['env']['FITME_FD'], str(fd))
                    created.append(fd)
                    os.write(fd, glb)
                    return types.SimpleNamespace(returncode=0)
                def memfd(_name):
                    if mode == 'unsupported':
                        raise OSError('not supported')
                    return os.dup(backing.fileno())
                with patch.object(runtime.os, 'memfd_create', None if mode == 'absent' else memfd, create=True), \
                     patch.object(runtime.tempfile, 'TemporaryFile', side_effect=fallback) as temp, \
                     patch.object(runtime.subprocess, 'run', side_effect=blender), \
                     patch.object(runtime, 'publish', return_value={'status':'ready'}) as publish:
                    response = runtime.render({'male':{}}, 'worker.py', subject='test')
                self.assertEqual(response.status_code, 200)
                publish.assert_called_once_with(glb, 'avatars', 'test')
                self.assertEqual(temp.call_count, 0 if mode == 'available' else 1)
                with self.assertRaises(OSError):
                    os.fstat(created[0])

    def test_blender_failure_closes_fallback_file(self):
        temporary_file = tempfile.TemporaryFile
        files = []
        def fallback(**kwargs):
            files.append(temporary_file())
            return files[-1]
        with patch.object(runtime.os, 'memfd_create', None, create=True), \
             patch.object(runtime.tempfile, 'TemporaryFile', side_effect=fallback), \
             patch.object(runtime.subprocess, 'run', side_effect=FileNotFoundError):
            with self.assertRaises(HTTPException) as raised:
                runtime.render({}, 'worker.py')
        self.assertEqual(raised.exception.status_code, 503)
        self.assertTrue(files[0].closed)
