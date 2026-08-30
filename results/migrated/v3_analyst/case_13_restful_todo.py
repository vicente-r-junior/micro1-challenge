import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

TODOS = {
    'todo1': {'task': 'build an API'},
    'todo2': {'task': '?????'},
    'todo3': {'task': 'profit!'},
}

_BAD_REQUEST_MESSAGE = 'The browser (or proxy) sent a request that this server could not understand.'
_METHOD_NOT_ALLOWED_MESSAGE = 'The method is not allowed for the requested URL.'
_NOT_FOUND_MESSAGE = ('The requested URL was not found on the server. If you entered the URL manually '
                      'please check your spelling and try again.')


@app.exception_handler(StarletteHTTPException)
async def _http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 405:
        return JSONResponse(status_code=405, content={'message': _METHOD_NOT_ALLOWED_MESSAGE})
    if exc.status_code == 404:
        return JSONResponse(status_code=404, content={'message': _NOT_FOUND_MESSAGE})
    return JSONResponse(status_code=exc.status_code, content={'detail': exc.detail})


def _not_found(todo_id: str) -> JSONResponse:
    return JSONResponse(status_code=404, content={'message': f"Todo {todo_id} doesn't exist"})


def _coerce(value):
    if value is None:
        return None
    return str(value)


async def _get_task(request: Request):
    """Mirror flask-restful reqparse lookup order: JSON body, then form, then args.
    Values are coerced with str(); malformed JSON bodies raise 400 like Flask."""
    content_type = request.headers.get('content-type', '')
    if 'application/json' in content_type or '+json' in content_type:
        raw = await request.body()
        if raw:
            try:
                data = json.loads(raw)
            except (ValueError, TypeError):
                return None, JSONResponse(status_code=400, content={'message': _BAD_REQUEST_MESSAGE})
            if isinstance(data, dict) and 'task' in data:
                return _coerce(data['task']), None
    form = await request.form()
    if 'task' in form:
        return _coerce(form['task']), None
    task = request.query_params.get('task')
    if task is not None:
        return _coerce(task), None
    return None, None


@app.get('/todos')
async def list_todos():
    return TODOS


@app.post('/todos')
async def create_todo(request: Request):
    task, err = await _get_task(request)
    if err is not None:
        return err
    todo_id = f'todo{len(TODOS) + 1}'
    TODOS[todo_id] = {'task': task}
    return JSONResponse(content={'task': task}, status_code=201)


@app.get('/todos/{todo_id}')
async def get_todo(todo_id: str):
    if todo_id not in TODOS:
        return _not_found(todo_id)
    return TODOS[todo_id]


@app.put('/todos/{todo_id}')
async def update_todo(todo_id: str, request: Request):
    task, err = await _get_task(request)
    if err is not None:
        return err
    todo = {'task': task}
    TODOS[todo_id] = todo
    return JSONResponse(content=todo, status_code=201)


@app.delete('/todos/{todo_id}')
async def delete_todo(todo_id: str):
    if todo_id not in TODOS:
        return _not_found(todo_id)
    del TODOS[todo_id]
    return Response(status_code=204)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
