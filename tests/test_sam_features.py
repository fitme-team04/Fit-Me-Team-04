# 역할: 기존 ML 계약과 직접 SAM 메시 생성 파이프라인을 검사합니다.
import asyncio
import importlib
from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from PIL import Image
from fastapi import HTTPException
from fastapi.testclient import TestClient

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE/'avatar/src'))
from core.contract import MEASUREMENT_KEYS, PREDICTION_KEYS, prepare_prediction
from core.features import make_features, validate_features, SAM_MEASUREMENT_KEYS


class FeatureTests(unittest.TestCase):
    def test_normalized_cm_values_are_invariant_to_model_scale(self):
        measures = {key: 180. if key == 'height_cm' else 45. for key in (*SAM_MEASUREMENT_KEYS, 'height_cm')}
        result = make_features(measures, 175., 70.)
        scaled = make_features({key: value*2 for key, value in measures.items()}, 175., 70.)
        self.assertEqual(result, scaled)
        self.assertEqual(set(result['sam_measurements']), set(SAM_MEASUREMENT_KEYS))
        self.assertEqual(set(result['sam_measurements'].values()), {43.75})
        self.assertNotIn('height_cm', result['sam_measurements'])
        for bad in [None, float('nan'), float('inf'), -1, 0, True, '45']:
            partial = make_features({**measures, 'knee_girth_cm': bad}, 175., 70.)
            self.assertIsNone(partial['sam_measurements']['knee_girth_cm'])
            self.assertEqual(partial['sam_measurements']['wrist_girth_cm'], 43.75)
        for bad in [None, 0, float('nan')]:
            with self.assertRaises(ValueError):
                make_features({**measures, 'height_cm': bad}, 175., 70.)

    def test_nulls_are_serializable_and_obviously_invalid_lengths_are_null(self):
        import json
        values = {key: 40. for key in SAM_MEASUREMENT_KEYS}
        values.update(inseam_cm=200., hip_line_height_cm=-1., wrist_girth_cm=None)
        result = make_features({'height_cm': 175., **values}, 175., 70.)
        self.assertIsNone(result['sam_measurements']['inseam_cm'])
        self.assertIsNone(result['sam_measurements']['hip_line_height_cm'])
        self.assertIsNone(result['sam_measurements']['wrist_girth_cm'])
        self.assertEqual(json.loads(json.dumps(result, allow_nan=False)), result)
        empty = make_features({'height_cm': 175., **dict.fromkeys(SAM_MEASUREMENT_KEYS)}, 175., 70.)
        self.assertTrue(all(v is None for v in empty['sam_measurements'].values()))

    def test_uploadable_feature_and_connection_modules_stay_in_sync(self):
        core = (BASE/'avatar/src/core/features.py').read_text(encoding='utf-8')
        standalone = (BASE/'avatar/azureml/features.py').read_text(encoding='utf-8')
        self.assertEqual(core, standalone)
        self.assertEqual((BASE/'avatar/src/core/contract.py').read_text(encoding='utf-8'),
                         (BASE/'avatar/azureml/contract.py').read_text(encoding='utf-8'))

    def test_13_inputs_and_28_predictions_preserve_input_height(self):
        measures = {key: 180. if key == 'height_cm' else 45. for key in (*SAM_MEASUREMENT_KEYS, 'height_cm')}
        features = make_features(measures, 175., 70.)
        self.assertEqual(len(features['sam_measurements']), 11)
        self.assertNotIn('ratios', features)
        prediction = {'male': {key: 40. for key in PREDICTION_KEYS}}
        job = prepare_prediction(prediction, 175.)
        self.assertEqual(job['male']['height_cm'], 175.)
        for invalid in [dict(prediction['male'], height_cm=170.),
                        {key: value for key, value in prediction['male'].items() if key!='chest_girth_cm'},
                        dict(prediction['male'], chest_girth_cm=None)]:
            with self.assertRaises(ValueError):
                prepare_prediction({'male': invalid}, 175.)
        for changed in [dict(features, ratios={}), dict(features, schema_version=1),
                        dict(features, sam_measurements={}),
                        dict(features, sam_measurements={**features['sam_measurements'], 'chest_girth_cm': 40})]:
            with self.assertRaises(ValueError):
                validate_features(changed)



class PipelineTests(unittest.TestCase):
    def test_direct_sam_pipeline_skips_ml_and_renders_while_surface_exists(self):
        api = importlib.import_module('api.avatar')
        stream = BytesIO()
        Image.new('RGB', (8, 8)).save(stream, format='PNG')
        temp_factory = tempfile.TemporaryDirectory
        for fail in (False, True):
            events = []
            def reconstruct(photo, folder):
                events.append('sam')
                surface = folder/'surface.npz'
                surface.write_bytes(b'test-sam-surface')
                return surface
            def render_sam(payload, worker, template, subject):
                events.append('render')
                self.assertEqual(worker,'sam_avatar_worker.py')
                self.assertEqual(payload['height_cm'],175.)
                self.assertEqual(Path(payload['surface_path']).read_bytes(),b'test-sam-surface')
                self.assertNotIn('male',payload)
                if fail:
                    raise HTTPException(503,'test SAM export failure')
                return {'ok': True}
            with temp_factory() as folder:
                template = Path(folder)/'template.blend'
                template.touch()
                with patch.dict('os.environ', {'FITME_TEMPLATE': str(template)}), \
                     patch.object(api.tempfile, 'TemporaryDirectory', side_effect=lambda **kw: temp_factory(dir=folder)), \
                     patch.object(api, 'reconstruct', side_effect=reconstruct), \
                     patch.object(api, 'measure_surface') as measure, \
                     patch.object(api, 'predict', new_callable=AsyncMock) as predict, \
                     patch.object(api, 'render', side_effect=render_sam):
                    api.app.dependency_overrides[api.principal] = lambda: 'test'
                    try:
                        response = TestClient(api.app).post('/api/avatars', content=stream.getvalue(),
                            headers={'height-cm': '175', 'weight-kg': '70'})
                    finally:
                        api.app.dependency_overrides.clear()
                self.assertEqual(response.status_code, 503 if fail else 200, response.text)
                self.assertEqual(events, ['sam','render'])
                measure.assert_not_called()
                predict.assert_not_called()
