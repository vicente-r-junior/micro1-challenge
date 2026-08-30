from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

todos = {}


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 405:
        return JSONResponse(
            status_code=405,
            content={"message": "The method is not allowed for the requested URL."},
            headers=exc.headers,
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(content={"message": "Internal Server Error"}, status_code=500)


@app.get("/{todo_id}")
def get_todo(todo_id: str):
    return {todo_id: todos[todo_id]}


@app.put("/{todo_id}")
async def put_todo(todo_id: str, request: Request):
    try:
        form = await request.form()
        data = form["data"]
    except KeyError:
        return JSONResponse(
            status_code=400,
            content={"message": "The browser (or proxy) sent a request that this server could not understand."},
        )
    todos[todo_id] = data
    return {todo_id: data}
