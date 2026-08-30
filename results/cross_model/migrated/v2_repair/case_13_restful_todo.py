from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
import json
from urllib.parse import parse_qs

app = FastAPI()

TODOS = {
    'todo1': {'task': 'build an API'},
    'todo2': {'task': '?????'},
    'todo3': {'task': 'profit!'},
}

def abort_if_todo_doesnt_exist(todo_id: str):
    if todo_id not in TODOS:
        return JSONResponse(content={'message': "Todo {} doesn't exist".format(todo_id)}, status_code=404)
    return None

async def parse_task(request: Request):
    body = await request.body()
    content_type = request.headers.get('content-type', '')
    mimetype = content_type.split(';')[0].strip().lower()

    is_json = mimetype == 'application/json' or (
        mimetype.startswith('application/') and mimetype.endswith('+json')
    )
    if is_json:
        try:
            data = json.loads(body.decode('utf-8'))
        except Exception:
            return JSONResponse(
                content={'message': 'The browser (or proxy) sent a request that this server could not understand.'},
                status_code=400,
            )
        if isinstance(data, dict) and 'task' in data:
            return str(data['task'])

    if 'task' in request.query_params:
        return str(request.query_params['task'])

    if mimetype == 'application/x-www-form-urlencoded':
        try:
            parsed = parse_qs(body.decode('utf-8'), keep_blank_values=True)
            if 'task' in parsed:
                return str(parsed['task'][0])
        except Exception:
            pass
        return None

    if mimetype == 'multipart/form-data':
        try:
            form = await request.form()
            if 'task' in form:
                return str(form['task'])
        except Exception:
            pass
        return None

    return None

@app.exception_handler(StarletteHTTPException)
async def legacy_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 405:
        return JSONResponse(
            content={'message': 'The method is not allowed for the requested URL.'},
            status_code=405,
        )
    return JSONResponse(
        content={'detail': exc.detail},
        status_code=exc.status_code,
        headers=getattr(exc, 'headers', None),
    )

@app.get('/todos')
async def list_todos():
    return TODOS

@app.post('/todos')
async def post_todo(request: Request):
    task = await parse_task(request)
    if isinstance(task, Response):
        return task
    todo_id = 'todo%d' % (len(TODOS) + 1)
    TODOS[todo_id] = {'task': task}
    return JSONResponse(content=TODOS[todo_id], status_code=201)

@app.get('/todos/{todo_id}')
async def get_todo(todo_id: str):
    error = abort_if_todo_doesnt_exist(todo_id)
    if error:
        return error
    return TODOS[todo_id]

@app.delete('/todos/{todo_id}')
async def delete_todo(todo_id: str):
    error = abort_if_todo_doesnt_exist(todo_id)
    if error:
        return error
    del TODOS[todo_id]
    return Response(status_code=204)

@app.put('/todos/{todo_id}')
async def put_todo(todo_id: str, request: Request):
    task = await parse_task(request)
    if isinstance(task, Response):
        return task
    TODOS[todo_id] = {'task': task}
    return JSONResponse(content=TODOS[todo_id], status_code=201)
