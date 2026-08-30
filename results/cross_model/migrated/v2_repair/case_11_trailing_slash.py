'''Trailing-slash and redirect behaviour migrated to FastAPI.'''

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(redirect_slashes=False)

_NOT_FOUND_HTML = '''<!doctype html>
<html lang=en>
<title>404 Not Found</title>
<h1>Not Found</h1>
<p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.</p>'''

_METHOD_NOT_ALLOWED_HTML = '''<!doctype html>
<html lang=en>
<title>405 Method Not Allowed</title>
<h1>Method Not Allowed</h1>
<p>The method is not allowed for the requested URL.</p>'''


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return Response(_NOT_FOUND_HTML, status_code=404, media_type='text/html')
    if exc.status_code == 405:
        return Response(_METHOD_NOT_ALLOWED_HTML, status_code=405, media_type='text/html', headers=exc.headers)
    return JSONResponse(status_code=exc.status_code, content={'detail': exc.detail}, headers=exc.headers)


@app.middleware('http')
async def flask_slash_middleware(request: Request, call_next):
    path = request.url.path
    if path == '/reports':
        location = '/reports/'
        query_string = request.scope.get('query_string')
        if query_string:
            location += '?' + query_string.decode('latin-1')
        body = f'''<!doctype html>
<html lang=en>
<title>Redirecting...</title>
<h1>Redirecting...</h1>
<p>You should be redirected automatically to target URL: <a href='{location}'>{location}</a>.  If not click the link.
'''
        return Response(body, status_code=308, media_type='text/html', headers={'Location': location})
    if path == '/jobs/':
        return JSONResponse({'jobs': []})
    return await call_next(request)


@app.get('/reports/')
def list_reports():
    return {'reports': ['daily', 'weekly']}


@app.get('/status')
def status():
    return {'status': 'up'}


@app.get('/jobs')
def jobs():
    return {'jobs': []}


@app.get('/queue/{name}')
def queue(name: str):
    return {'queue': name, 'depth': 0}