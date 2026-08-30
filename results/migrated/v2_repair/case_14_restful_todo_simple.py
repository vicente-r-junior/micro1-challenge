import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

todos = {}


class FlaskStyleJSONResponse(JSONResponse):
    def render(self, content):
        return (json.dumps(content) + "\n").encode("utf-8")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 405:
        return FlaskStyleJSONResponse(
            {"message": "The method is not allowed for the requested URL."},
            status_code=405,
        )
    if exc.status_code == 404:
        return FlaskStyleJSONResponse(
            {
                "message": "The requested URL was not found on the server. "
                "If you entered the URL manually please check your spelling and try again."
            },
            status_code=404,
        )
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.get("/{todo_id}")
def get_todo(todo_id: str):
    try:
        return FlaskStyleJSONResponse({todo_id: todos[todo_id]})
    except KeyError:
        return FlaskStyleJSONResponse(
            {"message": "Internal Server Error"}, status_code=500
        )


@app.put("/{todo_id}")
async def put_todo(todo_id: str, request: Request):
    try:
        form = await request.form()
    except Exception:
        form = None
    value = None
    if form is not None:
        value = next(
            (item for item in form.getlist("data") if isinstance(item, str)),
            None,
        )
    if value is None:
        return FlaskStyleJSONResponse(
            {"message": "The browser (or proxy) sent a request that this server could not understand."},
            status_code=400,
        )
    todos[todo_id] = value
    return FlaskStyleJSONResponse({todo_id: todos[todo_id]})
