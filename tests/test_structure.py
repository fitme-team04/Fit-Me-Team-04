# 역할: 재분류한 모듈·Docker 경로와 키·몸무게 ML 계약을 회귀 검사합니다.
import ast
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'avatar/azureml'))
from features import INPUT_COLUMNS, SAM_MEASUREMENT_KEYS
FEATURES = {'schema_version': 2, 'measurement_method': 'sam_surface_sections_11_v2',
            'height_cm': 175, 'weight_kg': 70, 'sam_measurements': {key: 40. for key in SAM_MEASUREMENT_KEYS}}
IDENTIFIER = 'a' * 32


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class StructureTests(unittest.TestCase):
    def test_local_imports_resolve_in_both_services(self):
        packages = {'api', 'core', 'geometry', 'storage', 'inference', 'database', 'checks'}
        for service in ('avatar', 'garment'):
            src = BASE / service / 'src'
            for path in list(src.rglob('*.py')) + list((BASE / service / 'scripts').glob('*.py')):
                tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module and node.module.split('.')[0] in packages:
                        target = src / node.module.replace('.', '/')
                        self.assertTrue(target.with_suffix('.py').is_file() or (target / '__init__.py').is_file(),
                                        f'{path}: unresolved {node.module}')

    def test_role_headers_and_removed_validation(self):
        for service in ('avatar', 'garment'):
            home = BASE / service
            self.assertFalse((home / 'validation').exists())
            for folder in ['src', 'scripts', 'azureml']:
                for path in (home / folder).rglob('*.py'):
                    self.assertTrue(path.read_text(encoding='utf-8').splitlines()[0].startswith('# 역할:'), str(path))

    def test_blender_and_sam_paths_exist(self):
        self.assertTrue((BASE / 'avatar/src/geometry/worker.py').is_file())
        self.assertTrue((BASE / 'avatar/src/inference/sam_reference.py').is_file())
        self.assertTrue((BASE / 'garment/src/geometry/garment_worker.py').is_file())
        for service, endpoint in [('avatar', 'api.avatar:app'), ('garment', 'api.garments:app')]:
            docker = (BASE / service / 'Dockerfile').read_text(encoding='utf-8')
            self.assertIn(endpoint, docker)
            self.assertNotIn('python check_generation.py', docker)

    def test_no_blob_originals_are_bundled(self):
        for name in ['mhr_model.pt', 'fitme_depth_fixed.blend', 'a_pose.npz', 'sam_body.npz']:
            self.assertFalse((BASE / 'avatar/models' / name).exists())


class ScoreTests(unittest.TestCase):
    def setUp(self):
        self.contract = load('score_contract', BASE / 'avatar/azureml/contract.py')
        with patch.dict(sys.modules, {'contract': self.contract}):
            self.score = load('score_under_test', BASE / 'avatar/azureml/score.py')
        self.prediction = {'male': {key: 175 if key == 'height_cm' else 40
                                  for key in self.contract.PREDICTION_KEYS}}
        self.score.predictor = MagicMock()
        self.score.predictor.predict.return_value = self.prediction

    def test_ml_receives_height_weight_and_ratios_in_json(self):
        result = self.score.run(json.dumps(FEATURES))
        self.score.predictor.predict.assert_called_once_with(height_cm=175, weight_kg=70, sam_measurements=FEATURES['sam_measurements'])
        self.assertEqual(result, self.prediction)
        self.assertNotIn('reference_pose', result['male'])

    def test_invalid_inputs_and_legacy_contract_rejected(self):
        for payload in [{'request_id': 'old'}, {'height_cm': True, 'weight_kg': 70},
                        {'height_cm': float('nan'), 'weight_kg': 70},
                        {'height_cm': 175, 'weight_kg': 70, 'photo': 'forbidden'}]:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.score.run(payload)

    def test_incomplete_measurements_rejected(self):
        self.score.predictor.predict.return_value = {'male': {'height_cm': 175}}
        with self.assertRaises(ValueError):
            self.score.run(FEATURES)
