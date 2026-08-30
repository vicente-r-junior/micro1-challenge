import json

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(redirect_slashes=False)

_TASKS = {1: {'id': 1, 'title': 'write migration', 'done': False}}

DEFAULT_404_HTML = '''<!doctype html>
<html lang=en>
<title>404 Not Found</title>
<h1>Not Found</h1>
<p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.</p>
</html>
'''

DEFAULT_405_HTML = '''<!doctype html>
<html lang=en>
<title>405 Method Not Allowed</title>
<h1>Method Not Allowed</h1>
<p>The method is not allowed for the requested URL.</p>
</html>
'''

class FlaskJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=True,
            allow_nan=True,
            indent=None,
            separators=(',', ':'),
            sort_keys=True,
        ).encode('utf-8')


async def _get_json_silent(request: Request):
    content_type = request.headers.get('content-type', '').lower()
    if 'application/json' not in content_type and '+json' not in content_type:
        return {}
    try:
        data = await request.json()
    except Exception:
        return {}
    return data or {}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return HTMLResponse(DEFAULT_404_HTML, status_code=404)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return HTMLResponse(DEFAULT_404_HTML, status_code=404)
    if exc.status_code == 405:
        return HTMLResponse(DEFAULT_405_HTML, status_code=405, headers=exc.headers)
    return FlaskJSONResponse({'detail': exc.detail}, status_code=exc.status_code)


@app.get('/tasks')
async def get_tasks():
    return FlaskJSONResponse({'tasks': list(_TASKS.values())})


@app.post('/tasks')
async def post_tasks(request: Request):
    data = await _get_json_silent(request)
    if 'title' not in data:
        return FlaskJSONResponse({'error': 'title is required'}, status_code=400)
    return FlaskJSONResponse({'id': 2, 'title': data['title'], 'done': False}, status_code=201)


@app.get('/tasks/{task_id}')
async def get_task(task_id: int):
    task = _TASKS.get(task_id)
    if task is None:
        return FlaskJSONResponse({'error': 'task not found'}, status_code=404)
    return FlaskJSONResponse(task)


@app.put('/tasks/{task_id}')
async def put_task(task_id: int, request: Request):
    task = _TASKS.get(task_id)
    if task is None:
        return FlaskJSONResponse({'error': 'task not found'}, status_code=404)
    data = await _get_json_silent(request)
    if 'title' not in data:
        return FlaskJSONResponse({'error': 'title is required'}, status_code=400)
    return FlaskJSONResponse({**task, 'title': data['title']})


@app.delete('/tasks/{task_id}')
async def delete_task(task_id: int):
    if task_id not in _TASKS:
        return FlaskJSONResponse({'error': 'task not found'}, status_code=404)
    return FlaskJSONResponse({'deleted': task_id})