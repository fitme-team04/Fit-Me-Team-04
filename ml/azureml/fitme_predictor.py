# 역할: Designer에서 학습한 model-s와 model-c를 함께 불러와
#       키·몸무게 + SAM 11개(일부 또는 전부 null 가능)를 받아 치수 28개를 돌려줍니다.
#       - 받은 SAM 값 중 비어 있거나 비정상인 것만 model-s(키·몸무게 → SAM 11개)로 채움
#       - 채운 SAM 11개 + 키·몸무게로 model-c가 상체 17개 예측
#       - 응답: 받은 실측값은 그대로, 채운 값과 예측값은 소수 첫째 자리로 반올림
import json
import logging
import math
import os
from collections import defaultdict
from pathlib import Path

SAM_KEYS = (
    'inseam_cm', 'hip_girth_cm', 'hip_width_cm', 'hip_depth_cm', 'hip_line_height_cm',
    'ankle_girth_cm', 'calf_girth_cm', 'knee_girth_cm', 'thigh_girth_cm',
    'upper_arm_girth_cm', 'wrist_girth_cm',
)
TARGET_KEYS = (
    'torso_length_cm', 'shoulder_width_cm', 'arm_length_cm', 'waist_line_height_cm',
    'chest_line_height_cm', 'belly_girth_cm', 'waist_girth_cm', 'waist_width_cm',
    'waist_depth_cm', 'chest_girth_cm', 'chest_width_cm', 'chest_depth_cm',
    'back_width_cm', 'underbust_girth_cm', 'belly_front_cm', 'hip_rear_cm', 'rise_arc_cm',
)
SCORE_COLUMN = 'Scored Labels'


def _required_positive(name, value):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be a positive finite number')
    return float(value)


def _usable(value):
    """정상 측정값이면 float, null·NaN·0·음수·무한대·비숫자면 None."""
    if type(value) not in (int, float):
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    return float(value)


def _designer_model_dirs():
    root = Path(os.getenv('AZUREML_MODEL_DIR', '.'))
    found = [p for p in [root, *root.rglob('*')]
             if p.is_dir() and (p / '_schema.json').exists() and (p / 'data.ilearner').exists()]
    if not found:
        raise FileNotFoundError(f'Designer model files not found under {root}')
    return found


class DesignerModel:
    """Designer Train Model 출력 폴더 하나를 불러와 '세로로 쌓은' 형태로 예측합니다."""

    def __init__(self, model_dir):
        from azureml.studio.core.io.model_directory import ModelDirectory
        from azureml.studio.modules.ml.score.score_generic_module.score_generic_module import ScoreModelModule
        from azureml.designer.serving.dagengine.converter import create_dfd_from_dict
        from azureml.studio.common.datatable.data_table import DataTable

        self.path = Path(model_dir)
        self._create_dfd = create_dfd_from_dict
        self._data_table = DataTable
        self._scorer = ScoreModelModule()
        self._model = ModelDirectory.load(str(model_dir)).model
        with open(self.path / '_schema.json') as fp:
            self._schema = json.load(fp)
        self.columns = [c['name'] for c in self._schema.get('columnAttributes', []) if c.get('name')]

    def score(self, base, items):
        entry = defaultdict(list)
        for item in items:
            row = dict(base, item=item, value=0.0)
            for col in self.columns:
                entry[col].append(row.get(col))
        dfd = self._create_dfd(dict(entry), self._schema)
        result, = self._scorer.run(
            learner=self._model,
            test_data=self._data_table.from_dfd(dfd),
            append_or_result_only=True,
        )
        frame = result.data_frame
        return {str(i): float(s) for i, s in zip(frame['item'], frame[SCORE_COLUMN])}


class FitmePredictor:
    def __init__(self, model_dirs):
        self.model_c = None
        self.model_s = None
        for d in model_dirs:
            m = DesignerModel(d)
            # model-c는 입력에 SAM 치수 열이 있고, model-s는 키·몸무게만 있음
            if 'hip_girth_cm' in m.columns:
                self.model_c = m
            else:
                self.model_s = m
            logging.info('loaded designer model %s (%s)', d, 'model-c' if m is self.model_c else 'model-s')
        if self.model_c is None:
            raise FileNotFoundError('model-c (13 inputs) not found in the registered model')
        self.last_estimated = []

    def predict(self, height_cm, weight_kg, sam_measurements=None, **flat_measurements):
        unknown = set(flat_measurements) - set(SAM_KEYS)
        if unknown:
            raise ValueError(f'Unexpected fields: {sorted(unknown)}')
        raw = dict(sam_measurements or {})
        raw.update(flat_measurements)
        unknown = set(raw) - set(SAM_KEYS)
        if unknown:
            raise ValueError(f'Unexpected SAM fields: {sorted(unknown)}')

        body = {'height_cm': _required_positive('height_cm', height_cm),
                'weight_kg': _required_positive('weight_kg', weight_kg)}

        sam = {k: _usable(raw.get(k)) for k in SAM_KEYS}
        missing = [k for k in SAM_KEYS if sam[k] is None]

        if missing:
            if self.model_s is None:
                raise ValueError(f'Missing SAM measurements and model-s is not loaded: {missing}')
            filled = self.model_s.score(body, missing)
            for k in missing:
                sam[k] = round(filled[k], 1)
        self.last_estimated = missing

        upper = self.model_c.score(dict(body, **sam), TARGET_KEYS)

        male = {k: sam[k] for k in SAM_KEYS}
        male.update({k: round(upper[k], 1) for k in TARGET_KEYS})
        return {'male': male}


def load_predictor():
    return FitmePredictor(_designer_model_dirs())
