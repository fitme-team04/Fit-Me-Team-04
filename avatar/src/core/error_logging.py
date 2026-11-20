# 역할: 422·503 원인을 요청 본문·인증값 없이 서버 로그에 기록합니다.
import logging
import re
import json
from fastapi.responses import JSONResponse
from core.body_girths import body_girths

from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException


def register_error_logging(app):
    def with_empty_girths(request, response):
        if request.url.path.rstrip('/') == '/api/avatars':
            payload = json.loads(response.body)
            response.body = json.dumps({**payload, **body_girths()}, ensure_ascii=False).encode('utf-8')
            response.headers['content-length'] = str(len(response.body))
        return response

    @app.exception_handler(HTTPException)
    async def log_http_error(request, exc):
        if exc.status_code in (422, 503):
            detail = re.sub(r'https?://\S+', '[URL]', str(exc.detail))[:512]
            logging.warning('avatar response status=%s method=%s path=%s detail=%s',
                            exc.status_code, request.method, request.url.path, detail)
        return with_empty_girths(request, await http_exception_handler(request, exc))

    @app.exception_handler(RequestValidationError)
    async def log_validation_error(request, exc):
        fields = [(error['loc'], error['type']) for error in exc.errors()]
        logging.warning('avatar response status=422 method=%s path=%s validation=%s',
                        request.method, request.url.path, fields)
        return with_empty_girths(request, await request_validation_exception_handler(request, exc))

    @app.exception_handler(Exception)
    async def unexpected_error(request, exc):
        logging.error('avatar unexpected error method=%s path=%s type=%s',
                      request.method, request.url.path, type(exc).__name__)
        response = JSONResponse({'detail': 'Internal server error'}, status_code=500)
        return with_empty_girths(request, response)
