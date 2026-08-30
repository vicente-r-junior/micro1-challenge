from html import escape
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

FLASK_404_HTML = '''<!doctype html>
<html lang=en>
<title>404 Not Found</title>
<h1>Not Found</h1>
<p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.</p>
'''

FLASK_405_HTML = '''<!doctype html>
<html lang=en>
<title>405 Method Not Allowed</title>
<h1>Method Not Allowed</h1>
<p>The method is not allowed for the requested URL.</p>
'''

REDIRECT_HTML = '''<!doctype html>
<html lang=en>
<title>Redirecting...</title>
<h1>Redirecting...</h1>
<p>You should be redirected automatically to target URL: <a href="{location}">{location}</a>. If not click the link.</p>
'''

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.router.redirect_slashes = False

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return HTMLResponse(FLASK_404_HTML, status_code=404)
    if exc.status_code == 405:
        return HTMLResponse(FLASK_405_HTML, status_code=405, headers={'Allow': 'GET, HEAD, OPTIONS'})
    headers = getattr(exc, 'headers', None)
    return JSONResponse({'detail': exc.detail}, status_code=exc.status_code, headers=headers)

@app.middleware('http')
async def flask_slash_compat(request: Request, call_next):
    path = request.scope['path']
    if path == '/reports':
        location = '/reports/' + ('?' + request.url.query if request.url.query else '')
        body = REDIRECT_HTML.replace('{location}', escape(location))
        return HTMLResponse(body, status_code=308, headers={'Location': location})
    if path == '/jobs/':
        request.scope['path'] = '/jobs'
    return await call_next(request)

@app.get('/reports/')
def list_reports():
    return JSONResponse({'reports': ['daily', 'weekly']})

@app.get('/status')
def status():
    return JSONResponse({'status': 'up'})

@app.get('/jobs')
def jobs():
    return JSONResponse({'jobs': []})

@app.get('/queue/{name}')
def queue(name: str):
    return JSONResponse({'queue': name, 'depth': 0})