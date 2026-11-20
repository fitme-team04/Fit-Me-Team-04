# 역할: Studio 추론의 출력 매핑·숫자 검증·모델 자동 탐색과 입력 피처를 검사합니다.
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'avatar/azureml'))
from features import INPUT_COLUMNS, SAM_MEASUREMENT_KEYS
FEATURES = {'schema_version': 2, 'measurement_method': 'sam_surface_sections_11_v2',
            'height_cm': 175, 'weight_kg': 70, 'sam_measurements': {key: 40. for key in SAM_MEASUREMENT_KEYS}}
IDENTIFIER = 'a' * 32


class StudioScoreTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('studio_score_test', BASE / 'avatar/azureml/score_studio.py')
        self.score = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.score)
        self.values = {key: 175 if key == 'height_cm' else 40 for key in self.score.MEASUREMENT_KEYS}

    def test_named_measurements_match_vm_contract(self):
        result = self.score.normalize_prediction({'male': self.values})
        self.assertEqual(result, {'male': self.values})
        with self.assertRaises(ValueError):
            self.score.normalize_prediction({**self.values, 'height_cm': 175})

    def test_unnamed_vector_requires_explicit_target_order(self):
        keys = [key for key in self.score.MEASUREMENT_KEYS if key != 'height_cm']
        with self.assertRaises(ValueError):
            self.score.normalize_prediction([[40] * len(keys)])
        self.score.config = {'output_columns': keys}
        self.assertEqual(self.score.normalize_prediction([[40] * len(keys)])['male'], self.values)

    def test_rejects_missing_unknown_nonfinite_and_boolean_outputs(self):
        for change in [{'arm_length_cm': True}, {'arm_length_cm': float('nan')},
                       {'arm_length_cm': '40'}, {'unknown': 40}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.score.normalize_prediction({**self.values, **change})
        with self.assertRaises(ValueError):
            self.score.normalize_prediction({'height_cm': 175})

    def test_json_supplies_all_30_features_in_configured_order(self):
        self.score.config = {'input_columns': list(INPUT_COLUMNS)}
        self.score.model = MagicMock()
        self.score.model.predict.return_value = self.values
        dataframe = MagicMock(return_value='test-frame')
        with patch.dict(sys.modules, {'pandas': types.SimpleNamespace(DataFrame=dataframe)}):
            result = self.score.run(FEATURES)
        dataframe.assert_called_once_with([[175, 70] + [40.] * 11], columns=list(INPUT_COLUMNS))
        self.score.model.predict.assert_called_once_with('test-frame')
        self.assertEqual(result, {'male': self.values})
        for payload in [{'request_id': 'old'}, {'height_cm': True, 'weight_kg': 70}]:
            with self.assertRaises(ValueError):
                self.score.run(payload)

    def test_json_null_becomes_missing_numeric_value_for_model(self):
        import math
        self.score.config = {'input_columns': list(INPUT_COLUMNS)}
        self.score.model = MagicMock()
        self.score.model.predict.return_value = self.values
        dataframe = MagicMock(return_value='test-frame')
        features = dict(FEATURES, sam_measurements=dict(FEATURES['sam_measurements'], knee_girth_cm=None))
        with patch.dict(sys.modules, {'pandas': types.SimpleNamespace(DataFrame=dataframe)}):
            self.score.run(features)
        row = dataframe.call_args.args[0][0]
        self.assertTrue(math.isnan(row[list(INPUT_COLUMNS).index('knee_girth_cm')]))
        self.assertEqual(row[0:2], [175., 70.])

    def test_joblib_init_requires_unambiguous_model(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict('os.environ', {'AZUREML_MODEL_DIR': folder}, clear=True):
            with self.assertRaises(ValueError):
                self.score.init()
            model_path = Path(folder) / 'model.joblib'
            model_path.write_bytes(b'test-only')
            trained = MagicMock()
            trained.feature_names_in_ = list(INPUT_COLUMNS)
            loader = MagicMock(return_value=trained)
            with patch.dict(sys.modules, {'joblib': types.SimpleNamespace(load=loader)}):
                self.score.init()
            loader.assert_called_once_with(model_path)
            self.assertIs(self.score.model, trained)
