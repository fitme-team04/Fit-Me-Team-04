import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sizekorea_reference import configured_profiles, prepare


class ReferenceConversionTests(unittest.TestCase):
    def test_join_uses_id_and_normalizes_only_observed_measurements(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            body, weights, result = (folder / name for name in ("body.csv", "weights.csv", "reference.csv"))
            body.write_text("HUMAN_ID,키,가슴둘레,어깨사이너비\nx,1700,1011,420\ny,1600,910,9999\n"
                            "z,1650,9999,9999\nw,1730,1000,410\n", encoding="utf-8")
            weights.write_text("HUMAN_ID,weight_kg\ny,55\nx,71\nz,67\nother,58\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "체중"):
                prepare(body, result)
            self.assertEqual(prepare(body, result, weights), (2, 1, 1, 1))
            self.assertNotIn("HUMAN_ID", result.read_text(encoding="utf-8"))
            with patch.dict(os.environ, SIZEKOREA_REFERENCE_CSV=str(result)):
                people = configured_profiles()
                self.assertEqual(people[0], {"height": 170, "weight": 71,
                                             "measures": {"chest_girth": 101.1, "shoulder_width": 42}})
                self.assertEqual(people[1]["measures"], {"chest_girth": 91})
                previous = result.read_bytes()
                weights.write_text("HUMAN_ID,weight_kg\nx,71\nx,72\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "중복"):
                    prepare(body, result, weights)
                self.assertEqual(previous, result.read_bytes())
                body.write_text("HUMAN_ID,키,가슴둘레,weight_kg\nf,170,101,60\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "단위"):
                    prepare(body, result)
                result.write_text("bad,headers\n", encoding="utf-8")
                with self.assertRaises(RuntimeError):
                    configured_profiles()

    def test_missing_configuration_and_inaccessible_configured_path_are_distinct(self):
        with patch.dict(os.environ, SIZEKOREA_REFERENCE_CSV=""):
            self.assertIsNone(configured_profiles())
        with TemporaryDirectory() as tmp, patch.dict(os.environ, SIZEKOREA_REFERENCE_CSV=str(Path(tmp)/"absent")):
            with self.assertRaises(RuntimeError):
                configured_profiles()
