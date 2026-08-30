import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import StarletteHTTPException
from fastapi.responses import Response

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

TODOS = {
    'todo1': {'task': 'build an API'},
    'todo2': {'task': '?????'},
    'todo3': {'task': 'profit!'},
}


def _json_response(content, status_code=200):
    return Response(
        content=json.dumps(content, sort_keys=True).encode('utf-8'),
        status_code=status_code,
        media_type='application/json',
    )


def _todo_not_found(todo_id):
    return _json_response(
        {'message': "Todo {} doesn't exist".format(todo_id)},
        status_code=404,
    )


async def _parse_task(request: Request):
    # Flask-RESTful's default RequestParser locations are JSON first, then form.
    # Accessing request.json on a JSON-ish body that fails to parse raises the
    # Werkzeug 400 BadRequest ("The browser (or proxy) sent a request that this
    # server could not understand."); the default type of the argument is str,
    # so any non-None value is coerced with str().
    raw = await request.body()
    payload = None
    if raw:
        stripped = raw.lstrip()
        content_type = request.headers.get('content-type', '').lower()
        if stripped.startswith(b'{') or stripped.startswith(b'[') or 'json' in content_type:
            try:
                payload = json.loads(raw)
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail='The browser (or proxy) sent a request that this server could not understand.',
                )

    if isinstance(payload, dict):
        value = payload.get('task')
        if value is not None:
            return str(value)

    form = await request.form()
    value = form.get('task')
    if value is not None:
        return str(value)
    return None


@app.exception_handler(StarletteHTTPException)
async def _handle_http_exception(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        message = "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again."
    elif exc.status_code == 405:
        message = "The method is not allowed for the requested URL."
    else:
        message = exc.detail
    return _json_response({'message': message}, status_code=exc.status_code)


@app.get('/todos')
async def list_todos():
    return _json_response(TODOS)


@app.post('/todos')
async def create_todo(request: Request):
    task = await _parse_task(request)
    todo_id = 'todo%d' % (len(TODOS) + 1)
    TODOS[todo_id] = {'task': task}
    return _json_response(TODOS[todo_id], status_code=201)


@app.get('/todos/{todo_id}')
async def get_todo(todo_id: str):
    if todo_id not in TODOS:
        return _todo_not_found(todo_id)
    return _json_response(TODOS[todo_id])


@app.put('/todos/{todo_id}')
async def update_todo(todo_id: str, request: Request):
    task = await _parse_task(request)
    TODOS[todo_id] = {'task': task}
    return _json_response(TODOS[todo_id], status_code=201)


@app.delete('/todos/{todo_id}')
async def delete_todo(todo_id: str):
    if todo_id not in TODOS:
        return _todo_not_found(todo_id)
    del TODOS[todo_id]
    return Response(status_code=204, media_type='text/html')
