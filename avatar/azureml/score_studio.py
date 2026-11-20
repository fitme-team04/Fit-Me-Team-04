# 역할: 키·몸무게·SAM 측정값 11개로 등록 모델을 호출하고 치수 28개를 반환합니다.
import json
import math
import os
from numbers import Integral, Real
from pathlib import Path
from features import INPUT_COLUMNS, validate_features

from contract import PREDICTION_KEYS
MEASUREMENT_KEYS = tuple(sorted(PREDICTION_KEYS))
model = None
config = {}


def init():
    """Called once by Azure ML when the deployment starts."""
    global model, config
    root = Path(os.environ['AZUREML_MODEL_DIR']).resolve()
    explicit_config = os.getenv('FITME_MODEL_CONFIG', '').strip()
    config_path = Path(explicit_config) if explicit_config else Path(__file__).with_name('model_config.json')
    if explicit_config and not config_path.is_file():
        raise FileNotFoundError('FITME_MODEL_CONFIG does not exist')
    config = json.loads(config_path.read_text(encoding='utf-8')) if config_path.is_file() else {}
    columns = config.get('input_columns', list(INPUT_COLUMNS))
    if (not isinstance(columns, list) or not all(isinstance(name, str) for name in columns)
            or len(columns) != len(INPUT_COLUMNS) or len(set(columns)) != len(INPUT_COLUMNS)):
        raise ValueError('input_columns must name all 13 features in the documented order')
    output_columns = config.get('output_columns', [])
    if not isinstance(output_columns, list) or len(output_columns) != len(set(output_columns)):
        raise ValueError('output_columns must be a list of distinct target names')
    if set(output_columns) - set(MEASUREMENT_KEYS):
        raise ValueError('Map model outputs to the supported FitMe measurement codes')
    config['input_columns'] = columns
    configured_format = config.get('model_format', 'auto')
    selected = config.get('model_file', '')
    if selected:
        path = (root / selected).resolve()
        if not path.is_relative_to(root) or not path.exists():
            raise ValueError('model_file must exist inside AZUREML_MODEL_DIR')
    else:
        mlflow_paths = list(root.rglob('MLmodel'))
        if len(mlflow_paths) == 1:
            path = mlflow_paths[0].parent
        elif mlflow_paths:
            raise ValueError('Multiple MLflow models found; specify model_file')
        else:
            candidates = list(root.rglob('*.joblib')) + list(root.rglob('*.pkl'))
            if len(candidates) != 1:
                raise ValueError('Specify the exact registered model path in model_config.json')
            path = candidates[0]
    is_mlflow = path.is_dir() and (path / 'MLmodel').is_file()
    if configured_format == 'mlflow' or (configured_format == 'auto' and is_mlflow):
        import mlflow.pyfunc
        model = mlflow.pyfunc.load_model(str(path))
    elif configured_format == 'sklearn' or (configured_format == 'auto' and path.suffix in {'.pkl', '.joblib'}):
        # Only deserialize the team's trusted registered model.
        import joblib
        model = joblib.load(path)
        feature_count = getattr(model, 'n_features_in_', len(INPUT_COLUMNS))
        if isinstance(feature_count, Integral) and feature_count != len(INPUT_COLUMNS):
            raise ValueError('Model must be trained with height, weight and all 11 SAM cm measurements')
        feature_names = getattr(model, 'feature_names_in_', None)
        if feature_names is not None and list(feature_names) != columns:
            raise ValueError('input_columns differ from the model training feature names/order')
    else:
        raise ValueError('Supported model_format: auto, mlflow, sklearn; confirm the actual model format')
    if not callable(getattr(model, 'predict', None)):
        raise ValueError('The registered model must provide predict()')


def normalize_prediction(prediction):
    """Map named results, or an explicitly configured ordered vector, to FitMe."""
    if hasattr(prediction, 'columns') and hasattr(prediction, 'to_dict'):
        if len(prediction) != 1:
            raise ValueError('Expected one prediction row')
        # Config can rename training-specific columns, preserving their original order.
        configured = config.get('output_columns', [])
        if configured:
            if len(configured) != len(prediction.columns):
                raise ValueError('output_columns length differs from model output')
            values = dict(zip(configured, prediction.iloc[0].tolist()))
        else:
            values = prediction.to_dict(orient='records')[0]
    elif isinstance(prediction, dict):
        values = prediction.get('male', prediction)
        if not isinstance(values, dict):
            raise ValueError('Named prediction must be an object')
        values = dict(values)
    else:
        if hasattr(prediction, 'tolist'):
            prediction = prediction.tolist()
        if not isinstance(prediction, list) or len(prediction) != 1 or not isinstance(prediction[0], list):
            raise ValueError('Expected a single row of predicted measurements')
        columns = config.get('output_columns', [])
        if not columns or len(columns) != len(prediction[0]):
            raise ValueError('Set output_columns to the exact model target order; do not guess')
        values = dict(zip(columns, prediction[0]))
    if set(values) != set(MEASUREMENT_KEYS):
        raise ValueError('Model output must supply exactly 28 cm measurements without height_cm')
    normalized = {}
    for name, value in values.items():
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError('All 28 measurements must be numbers in cm')
        value = float(value)
        if not math.isfinite(value) or not 0 < value < 1000:
            raise ValueError('Measurements must be positive finite numbers below 1000 cm')
        normalized[name] = value
    return {'male': normalized}


def run(raw_data):
    if model is None:
        raise RuntimeError('Model has not been initialized')
    payload = json.loads(raw_data) if isinstance(raw_data, (str, bytes)) else raw_data
    features = validate_features(payload)
    flat = {**features['sam_measurements'], 'height_cm': features['height_cm'], 'weight_kg': features['weight_kg']}
    import pandas as pd
    frame = pd.DataFrame([[float('nan') if flat[key] is None else flat[key] for key in INPUT_COLUMNS]], columns=config['input_columns'])
    return normalize_prediction(model.predict(frame))
