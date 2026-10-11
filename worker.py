import os
import sys
from django.core.wsgi import get_wsgi_application

# Set path agar Django bisa ditemukan
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# Inisialisasi Django
application = get_wsgi_application()

# Entry point untuk Cloudflare Workers
async def fetch(request, env, ctx):
    from django.core.handlers.wsgi import WSGIHandler
    from io import BytesIO
    from urllib.parse import urlparse

    # Parse URL dari request Cloudflare
    parsed_url = urlparse(request.url)
    path = parsed_url.path or '/'
    query_string = parsed_url.query or ''

    # Konversi Request Cloudflare ke format WSGI Django
    environ = {
        'REQUEST_METHOD': request.method,
        'PATH_INFO': path,
        'QUERY_STRING': query_string,
        'SERVER_NAME': parsed_url.hostname or 'workers.dev',
        'SERVER_PORT': '443',
        'wsgi.url_scheme': 'https',
        'wsgi.input': BytesIO(await request.arrayBuffer()),
        'CONTENT_TYPE': request.headers.get('Content-Type', ''),
        'CONTENT_LENGTH': str(len(await request.arrayBuffer()) if request.body else 0),
    }

    # Masukkan headers
    for key, value in request.headers.items():
        environ[f'HTTP_{key.upper().replace("-", "_")}'] = value

    # Jalankan aplikasi Django
    response_started = False
    status_code = "200 OK"
    response_headers = []
    response_body = b""

    def start_response(status, headers, exc_info=None):
        nonlocal response_started, status_code, response_headers
        response_started = True
        status_code = status
        response_headers = headers

    result = application(environ, start_response)
    for chunk in result:
        response_body += chunk
    if hasattr(result, 'close'):
        result.close()

    # Konversi response Django kembali ke Response Cloudflare
    headers_dict = {k: v for k, v in response_headers}
    return Response(response_body, status=int(status_code.split(' ')[0]), headers=headers_dict)

# Helper class untuk Response (jika tidak menggunakan library eksternal)
class Response:
    def __init__(self, body, status=200, headers=None):
        self.body = body
        self.status = status
        self.headers = headers or {}