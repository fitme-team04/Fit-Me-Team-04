# 역할: 전신 사진 거절이 Blender 실행 없이 API의 재촬영 오류로 전달되는지 검사합니다.
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'avatar/src'))
from api import avatar
from core.sam_runtime import SAMInputError


class PhotoRejectionTests(unittest.TestCase):
    def test_resident_rejection_preserves_code_and_never_runs_blender(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(avatar,'runtime_mode',return_value='resident'), \
             patch.object(avatar.resident,'infer',side_effect=SAMInputError(code='full_body_required')), \
             patch.object(avatar.subprocess,'run') as run:
            with self.assertRaises(avatar.HTTPException) as failure:
                avatar.reconstruct(b'photo',Path(temp))
        self.assertEqual(failure.exception.status_code,422)
        self.assertEqual(failure.exception.detail['code'],'full_body_required')
        self.assertIn('다시 촬영',failure.exception.detail['message'])
        run.assert_not_called()

    def test_oneshot_rejection_uses_the_same_safe_photo_error(self):
        result=subprocess.CompletedProcess([],2,b'FITME_INPUT_ERROR full_body_required\n')
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(avatar,'runtime_mode',return_value='oneshot'), \
             patch.object(avatar.subprocess,'run',return_value=result):
            with self.assertRaises(avatar.HTTPException) as failure:
                avatar.reconstruct(b'photo',Path(temp))
        self.assertEqual(failure.exception.detail['code'],'full_body_required')


if __name__=='__main__':unittest.main()
