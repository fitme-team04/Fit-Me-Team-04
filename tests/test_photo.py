# 역할: 고해상도 사진 축소·EXIF 회전·입력 검증을 검사합니다.
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
from core.photo import prepare_photo, MAX_SAM_PIXELS


class PhotoTests(unittest.TestCase):
    def encoded(self, image, **kwargs):
        stream = BytesIO()
        image.save(stream, **kwargs)
        return stream.getvalue()

    def test_3744_by_5616_photo_is_resized_without_changing_aspect(self):
        data = self.encoded(Image.new('RGB', (3744, 5616), 'gray'), format='JPEG')
        with Image.open(BytesIO(prepare_photo(data))) as image:
            self.assertEqual(image.format, 'JPEG')
            self.assertLessEqual(image.width * image.height, MAX_SAM_PIXELS)
            self.assertLess(image.width, 3744)
            self.assertAlmostEqual(image.width / image.height, 3744 / 5616, places=3)

    def test_exif_rotation_is_applied_and_metadata_removed(self):
        exif = Image.Exif()
        exif[274] = 6
        data = self.encoded(Image.new('RGB', (40, 60)), format='JPEG', exif=exif)
        with Image.open(BytesIO(prepare_photo(data))) as image:
            self.assertEqual(image.size, (60, 40))
            self.assertIsNone(image.getexif().get(274))

    def test_transparent_png_uses_white_background(self):
        data = self.encoded(Image.new('RGBA', (8, 8), (0, 0, 0, 0)), format='PNG')
        with Image.open(BytesIO(prepare_photo(data))) as image:
            self.assertEqual(image.mode, 'RGB')
            self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))

    def test_invalid_and_over_limit_source_are_rejected(self):
        with self.assertRaises(OSError):
            prepare_photo(b'not an image')
        data = self.encoded(Image.new('RGB', (8, 8)), format='GIF')
        with self.assertRaises(ValueError):
            prepare_photo(data)
        with patch('core.photo.MAX_SOURCE_PIXELS', 10), self.assertRaises(ValueError):
            prepare_photo(self.encoded(Image.new('RGB', (8, 8)), format='JPEG'))
