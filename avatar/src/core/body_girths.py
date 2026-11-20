# 역할: 신체 API 응답에 ML 예측 둘레 세 개를 포함하고 실패 응답에서는 비웁니다.
GIRTH_KEYS = ('chest_girth_cm', 'waist_girth_cm', 'hip_girth_cm')


def body_girths(prediction=None):
    values = (prediction or {}).get('male', {})
    return {key: values.get(key) for key in GIRTH_KEYS}
