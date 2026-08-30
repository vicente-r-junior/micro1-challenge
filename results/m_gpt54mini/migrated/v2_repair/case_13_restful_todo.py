from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_404_NOT_FOUND

app = FastAPI()

TODOS = {
    'todo1': {'task': 'build an API'},
    'todo2': {'task': '?????'},
    'todo3': {'task': 'profit!'},
}


def abort_if_todo_doesnt_exist(todo_id):
    if todo_id not in TODOS:
        return JSONResponse(
            content={"message": "Todo {} doesn't exist".format(todo_id)},
            status_code=HTTP_404_NOT_FOUND,
        )
    return None


async def _parse_task(request: Request):
    try:
        form = await request.form()
        task = form.get('task')
        if task is None:
            json_data = await request.json()
            if isinstance(json_data, dict):
                task = json_data.get('task')
        return str(task) if task is not None else None
    except Exception:
        # Match Flask-RESTful / reqparse behavior for malformed input
        return JSONResponse(
            content={
                "message": "The browser (or proxy) sent a request that this server could not understand."
            },
            status_code=400,
        )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    if exc.status_code == 405:
        return JSONResponse(
            content={"message": "The method is not allowed for the requested URL."},
            status_code=405,
        )
    if exc.status_code == 404:
        return JSONResponse(
            content={"message": "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again."},
            status_code=404,
        )
    return JSONResponse(content={"detail": exc.detail}, status_code=exc.status_code)


@app.get('/todos')
async def get_todos():
    return TODOS


@app.post('/todos')
async def post_todo(request: Request):
    parsed = await _parse_task(request)
    if isinstance(parsed, JSONResponse):
        return parsed
    task = parsed
    todo_id = 'todo%d' % (len(TODOS) + 1)
    TODOS[todo_id] = {'task': task}
    return JSONResponse(content=TODOS[todo_id], status_code=HTTP_201_CREATED)


@app.get('/todos/{todo_id}')
async def get_todo(todo_id: str):
    err = abort_if_todo_doesnt_exist(todo_id)
    if err is not None:
        return err
    return TODOS[todo_id]


@app.delete('/todos/{todo_id}')
async def delete_todo(todo_id: str):
    err = abort_if_todo_doesnt_exist(todo_id)
    if err is not None:
        return err
    del TODOS[todo_id]
    return Response(status_code=HTTP_204_NO_CONTENT)


@app.put('/todos/{todo_id}')
async def put_todo(todo_id: str, request: Request):
    parsed = await _parse_task(request)
    if isinstance(parsed, JSONResponse):
        return parsed
    task = parsed
    task_obj = {'task': task}
    TODOS[todo_id] = task_obj
    return JSONResponse(content=task_obj, status_code=HTTP_201_CREATED)