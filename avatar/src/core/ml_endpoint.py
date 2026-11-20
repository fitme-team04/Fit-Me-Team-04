# 역할: Azure ML 실시간 엔드포인트 주소·인증 설정을 검증하고 요청 헤더를 만듭니다.
import os
import re
from urllib.parse import urlsplit


def endpoint_settings(environment=None):
    environment = os.environ if environment is None else environment
    endpoint = environment.get('AZURE_ML_ENDPOINT', '').strip()
    try:
        address = urlsplit(endpoint)
        valid = (address.scheme == 'https' and address.hostname
                 and address.hostname.endswith('.inference.ml.azure.com')
                 and address.port in (None, 443) and address.path.rstrip('/') == '/score'
                 and not address.username and not address.password and not address.query and not address.fragment)
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('Set AZURE_ML_ENDPOINT to the Azure ML HTTPS scoring URI')
    auth = environment.get('AZURE_ML_AUTH', 'aad_token').strip()
    if auth not in {'aad_token', 'key'}:
        raise ValueError('AZURE_ML_AUTH must be aad_token or key')
    if auth == 'key' and not environment.get('AZURE_ML_KEY', '').strip():
        raise ValueError('Key authentication requires AZURE_ML_KEY')
    deployment = environment.get('AZURE_ML_DEPLOYMENT', '').strip()
    if deployment and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,63}', deployment):
        raise ValueError('Invalid Azure ML deployment name')
    return endpoint, auth, deployment


def request_headers(auth, deployment):
    if auth == 'key':
        token = os.environ['AZURE_ML_KEY'].strip()
    else:
        from azure.identity import DefaultAzureCredential
        with DefaultAzureCredential() as credential:
            token = credential.get_token('https://ml.azure.com/.default').token
    headers = {'Authorization': 'Bearer '+token}
    if deployment:
        headers['azureml-model-deployment'] = deployment
    return headers
