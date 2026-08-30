import json

from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


FLASK_NOT_FOUND_HTML = '''<!doctype html>
<html lang=en>
<title>404 Not Found</title>
<h1>Not Found</h1>
<p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.</p>
'''

FLASK_METHOD_NOT_ALLOWED_HTML = '''<!doctype html>
<html lang=en>
<title>405 Method Not Allowed</title>
<h1>Method Not Allowed</h1>
<p>The method is not allowed for the requested URL.</p>
'''


def flask_json(payload):
    body = (json.dumps(payload, separators=(',', ':'), ensure_ascii=True, sort_keys=True) + chr(10)).encode('utf-8')
    return Response(content=body, media_type='application/json', headers={'Content-Type': 'application/json'})


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.router.redirect_slashes = False


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return Response(content=FLASK_NOT_FOUND_HTML, status_code=404, media_type='text/html')
    if exc.status_code == 405:
        return Response(
            content=FLASK_METHOD_NOT_ALLOWED_HTML,
            status_code=405,
            headers=exc.headers or {},
            media_type='text/html',
        )
    return Response(
        content=json.dumps({'detail': exc.detail}),
        status_code=exc.status_code,
        media_type='application/json',
    )


@app.get('/reports/')
def list_reports():
    return flask_json({'reports': ['daily', 'weekly']})


@app.api_route('/reports', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS', 'TRACE'], include_in_schema=False)
def redirect_reports(request: Request):
    location = '/reports/'
    if request.url.query:
        location = location + '?' + request.url.query
    return RedirectResponse(url=location, status_code=308)


@app.get('/status')
def status():
    return flask_json({'status': 'up'})


@app.get('/jobs')
def jobs():
    return flask_json({'jobs': []})


@app.get('/jobs/')
def jobs_trailing():
    return flask_json({'jobs': []})


@app.get('/queue/{name}')
def queue(name: str):
    return flask_json({'queue': name, 'depth': 0})