import json

from fastapi import FastAPI, Request
from fastapi.responses import Response
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

todos = {}


def json_response(data, status_code=200, headers=None):
    response_headers = {'Content-Type': 'application/json'}
    if headers:
        response_headers.update(headers)
    body = json.dumps(data) + chr(10)
    return Response(content=body, status_code=status_code, headers=response_headers)


_FLASK_HTTP_ERROR_DESCRIPTIONS = {
    400: 'The browser (or proxy) sent a request that this server could not understand.',
    404: 'The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.',
    405: 'The method is not allowed for the requested URL.',
    500: 'Internal Server Error',
}


@app.exception_handler(StarletteHTTPException)
async def flask_restful_http_exception_handler(request: Request, exc: StarletteHTTPException):
    message = _FLASK_HTTP_ERROR_DESCRIPTIONS.get(exc.status_code, exc.detail)
    return json_response({'message': message}, exc.status_code, getattr(exc, 'headers', None))


@app.get('/{todo_id}')
async def get_todo(todo_id: str):
    try:
        value = todos[todo_id]
    except KeyError:
        return json_response({'message': 'Internal Server Error'}, 500)
    return json_response({todo_id: value})


@app.put('/{todo_id}')
async def put_todo(todo_id: str, request: Request):
    form = await request.form()
    data = form.get('data')
    if not isinstance(data, str):
        return json_response(
            {
                'message': 'The browser (or proxy) sent a request that this server could not understand.'
            },
            400,
        )
    todos[todo_id] = data
    return json_response({todo_id: data})