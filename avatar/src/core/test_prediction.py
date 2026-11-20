# 역할: ML 없는 테스트 모드를 선택하고 입력 키에 비례한 예시 치수 28개를 제공합니다.
import json
import os
from pathlib import Path

from core.contract import prepare_prediction


def prediction_mode(environment=None):
    environment = os.environ if environment is None else environment
    mode = environment.get('FITME_PREDICTION_MODE', 'azure_ml').strip()
    if mode not in {'azure_ml', 'example'}:
        raise ValueError('FITME_PREDICTION_MODE must be azure_ml or example')
    return mode


def example_prediction(height_cm):
    fixture = json.loads(Path(__file__).with_name('test_measurements.json').read_text(encoding='utf-8'))
    scale = height_cm / fixture['reference_height_cm']
    values = {key: value * scale for key, value in fixture['male'].items()}
    job = prepare_prediction({'male': values}, height_cm)
    job['prediction_source'] = 'example'
    return job
