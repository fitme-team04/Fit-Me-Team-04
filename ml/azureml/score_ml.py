# 역할: 관리형 엔드포인트 진입점 (v2: SAM 일부·전부 null 지원).
#       3D팀 버전 2 요청(키·몸무게 + sam_measurements 11개, 실패 항목은 null)을 받아
#       {"male": {...28개...}}를 돌려줍니다. 어떤 항목을 추정했는지는 로그에 남깁니다.
import json
import logging

META_KEYS = {'schema_version', 'measurement_method'}


def init():
    global predictor
    from fitme_predictor import load_predictor
    predictor = load_predictor()
    logging.info('fitme predictor v2 loaded (model-s: %s)', predictor.model_s is not None)


def run(raw_data):
    payload = json.loads(raw_data) if isinstance(raw_data, (str, bytes)) else raw_data
    if not isinstance(payload, dict):
        raise ValueError('Expected a JSON object')
    for key in ('height_cm', 'weight_kg'):
        if key not in payload:
            raise ValueError(f'{key} is required')
    flat = {k: v for k, v in payload.items()
            if k not in META_KEYS | {'height_cm', 'weight_kg', 'sam_measurements'}}
    result = predictor.predict(
        height_cm=payload['height_cm'],
        weight_kg=payload['weight_kg'],
        sam_measurements=payload.get('sam_measurements'),
        **flat,
    )
    if predictor.last_estimated:
        logging.info('estimated SAM fields: %s', predictor.last_estimated)
    return result
