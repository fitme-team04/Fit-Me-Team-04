# 역할: FITME_ML_MEASUREMENTS 설정이 꺼져 있으면 ML을 부르지 않고, 켜면 ML 치수 28개를 핏 판정용 target으로만 붙이는지 검사합니다.
import importlib
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'avatar/src'))
from core.contract import PREDICTION_KEYS
from core.features import SAM_MEASUREMENT_KEYS

MEASURES = {'height_cm': 170., **{key: 40. for key in SAM_MEASUREMENT_KEYS}}
JOB = {'male': {**{key: 50. for key in PREDICTION_KEYS}, 'height_cm': 175., 'reference_pose': 'A'}}


class MLMeasurementTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.api = importlib.import_module('api.avatar')

    async def run_with(self, env, measure=MEASURES, predict=None):
        predict = predict or AsyncMock(return_value=JOB)
        with patch.dict(os.environ, env, clear=True), \
             patch.object(self.api, 'measure_surface', return_value=measure) as measured, \
             patch.object(self.api, 'predict', predict):
            result = await self.api.ml_prediction('surface.npz', 'template.blend', 175., 70.)
        return result, measured, predict

    async def test_default_is_off_and_never_measures_or_calls_ml(self):
        result, measured, predict = await self.run_with({})
        self.assertIsNone(result)
        measured.assert_not_called()
        predict.assert_not_called()

    async def test_on_sends_13_features_and_returns_only_28_predictions(self):
        result, measured, predict = await self.run_with({'FITME_ML_MEASUREMENTS': 'on'})
        features = predict.await_args.args[0]
        self.assertEqual(features['height_cm'], 175.)
        self.assertEqual(features['weight_kg'], 70.)
        self.assertEqual(set(features['sam_measurements']), set(SAM_MEASUREMENT_KEYS))
        self.assertAlmostEqual(features['sam_measurements']['hip_girth_cm'], 40. * 175 / 170)
        self.assertEqual(set(result), set(PREDICTION_KEYS))

    async def test_example_mode_is_never_used_for_fit_judgment(self):
        result, measured, predict = await self.run_with(
            {'FITME_ML_MEASUREMENTS': 'on', 'FITME_PREDICTION_MODE': 'example'})
        self.assertIsNone(result)
        predict.assert_not_called()

    async def test_ml_failure_falls_back_to_sam_measured_values(self):
        failing = AsyncMock(side_effect=HTTPException(504, 'Azure ML timed out'))
        result, _, _ = await self.run_with({'FITME_ML_MEASUREMENTS': 'on'}, predict=failing)
        self.assertIsNone(result)

    async def test_invalid_setting_is_treated_as_off(self):
        result, measured, _ = await self.run_with({'FITME_ML_MEASUREMENTS': 'yes'})
        self.assertIsNone(result)
        measured.assert_not_called()


if __name__ == '__main__':
    unittest.main()
