# 역할: 키·몸무게·SAM 측정값 11개를 팀 예측기에 전달하고 치수 28개를 반환합니다.
import json
from contract import validate_prediction

def init():
    global predictor
    from fitme_predictor import load_predictor
    predictor=load_predictor()

def run(raw_data):
    from features import validate_features
    payload=json.loads(raw_data) if isinstance(raw_data,(str,bytes)) else raw_data
    features = validate_features(payload)
    result = predictor.predict(height_cm=features['height_cm'], weight_kg=features['weight_kg'],
                               sam_measurements=features['sam_measurements'])
    return validate_prediction(result)
