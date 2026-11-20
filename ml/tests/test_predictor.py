# 역할: fitme_predictor의 null 처리·응답 형식을 Azure ML 없이 확인하는 회귀 테스트입니다.
#       실제 Designer 모델 대신 가짜 모델을 넣어, 어떤 항목을 채우고 어떻게 28개로 합치는지만 검사합니다.
#       실행: python -m unittest discover -s ml/tests -v
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'azureml'))
import fitme_predictor as fp  # noqa: E402


class FakeModel:
    def __init__(self, columns, value):
        self.columns = columns
        self.value = value
        self.calls = []

    def score(self, base, items):
        self.calls.append((dict(base), list(items)))
        return {item: self.value for item in items}


def make_predictor(with_model_s=True):
    p = fp.FitmePredictor.__new__(fp.FitmePredictor)
    p.model_c = FakeModel(['height_cm', 'weight_kg', *fp.SAM_KEYS, 'item', 'value'], 50.04)
    p.model_s = FakeModel(['height_cm', 'weight_kg', 'item', 'value'], 20.04) if with_model_s else None
    p.last_estimated = []
    return p


FULL = {k: 30.0 for k in fp.SAM_KEYS}


class PredictorTest(unittest.TestCase):
    def assert_28_positive(self, result):
        self.assertEqual(set(result), {'male'})
        male = result['male']
        self.assertEqual(set(male), set(fp.SAM_KEYS) | set(fp.TARGET_KEYS))
        self.assertEqual(len(male), 28)
        self.assertNotIn('height_cm', male)
        for value in male.values():
            self.assertIsInstance(value, float)
            self.assertTrue(math.isfinite(value) and value > 0)

    def test_full_11_skips_model_s(self):
        p = make_predictor()
        result = p.predict(175, 70, sam_measurements=FULL)
        self.assert_28_positive(result)
        self.assertEqual(p.model_s.calls, [])
        self.assertEqual(p.last_estimated, [])
        self.assertEqual(result['male']['hip_girth_cm'], 30.0)

    def test_partial_null_fills_only_missing(self):
        p = make_predictor()
        sam = dict(FULL, hip_girth_cm=None, wrist_girth_cm=None)
        result = p.predict(175, 70, sam_measurements=sam)
        self.assert_28_positive(result)
        self.assertEqual(p.model_s.calls[0][1], ['hip_girth_cm', 'wrist_girth_cm'])
        self.assertEqual(result['male']['hip_girth_cm'], 20.0)
        self.assertEqual(result['male']['inseam_cm'], 30.0)

    def test_invalid_values_are_treated_as_missing(self):
        p = make_predictor()
        sam = dict(FULL, knee_girth_cm=0, calf_girth_cm=float('nan'), ankle_girth_cm=-3, thigh_girth_cm='56')
        p.predict(175, 70, sam_measurements=sam)
        self.assertEqual(sorted(p.last_estimated),
                         ['ankle_girth_cm', 'calf_girth_cm', 'knee_girth_cm', 'thigh_girth_cm'])

    def test_all_null_fills_all_11(self):
        p = make_predictor()
        result = p.predict(175, 70, sam_measurements={k: None for k in fp.SAM_KEYS})
        self.assert_28_positive(result)
        self.assertEqual(len(p.last_estimated), 11)

    def test_model_c_receives_filled_values(self):
        p = make_predictor()
        p.predict(175, 70, sam_measurements=dict(FULL, hip_girth_cm=None))
        base, items = p.model_c.calls[0]
        self.assertEqual(base['hip_girth_cm'], 20.0)
        self.assertEqual(items, list(fp.TARGET_KEYS))

    def test_missing_without_model_s_raises(self):
        p = make_predictor(with_model_s=False)
        with self.assertRaises(ValueError):
            p.predict(175, 70, sam_measurements=dict(FULL, hip_girth_cm=None))

    def test_unknown_or_invalid_body_rejected(self):
        p = make_predictor()
        with self.assertRaises(ValueError):
            p.predict(175, 70, sam_measurements=dict(FULL, bad_cm=1))
        with self.assertRaises(ValueError):
            p.predict(0, 70, sam_measurements=FULL)


if __name__ == '__main__':
    unittest.main()
