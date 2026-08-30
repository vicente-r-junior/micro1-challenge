import json
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class FlaskJSONResponse(JSONResponse):
    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        return (json.dumps(content, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, redirect_slashes=False)

_TASKS = {1: {"id": 1, "title": "write migration", "done": False}}

_HTML_ERROR_BODIES = {
    404: "<!doctype html>\n"
    "<html lang=en>\n"
    "<title>404 Not Found</title>\n"
    "<h1>Not Found</h1>\n"
    "<p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.</p>\n",
    405: "<!doctype html>\n"
    "<html lang=en>\n"
    "<title>405 Method Not Allowed</title>\n"
    "<h1>Method Not Allowed</h1>\n"
    "<p>The method is not allowed for the requested URL.</p>\n",
    500: "<!doctype html>\n"
    "<html lang=en>\n"
    "<title>500 Internal Server Error</title>\n"
    "<h1>Internal Server Error</h1>\n"
    "<p>The server encountered an internal error and was unable to complete your request. Either the server is overloaded or there is an error in the application.</p>\n",
}


@app.exception_handler(StarletteHTTPException)
async def flask_http_exception_handler(request: Request, exc: StarletteHTTPException):
    body = _HTML_ERROR_BODIES.get(exc.status_code)
    if body is None:
        body = (
            f"<!doctype html>\n<html lang=en>\n<title>{exc.status_code} Error</title>\n"
            f"<h1>Error</h1>\n<p>{exc.detail}</p>\n"
        )
    return HTMLResponse(content=body, status_code=exc.status_code, headers=exc.headers)


def _is_json_mimetype(content_type: str) -> bool:
    mimetype = content_type.split(";", 1)[0].strip().lower()
    return mimetype == "application/json" or (mimetype.startswith("application/") and mimetype.endswith("+json"))


async def _get_json_silent(request: Request) -> Any:
    if not _is_json_mimetype(request.headers.get("content-type", "")):
        return None
    try:
        return json.loads(await request.body())
    except Exception:
        return None


def _server_error_response() -> HTMLResponse:
    return HTMLResponse(content=_HTML_ERROR_BODIES[500], status_code=500)


def _extract_title_or_error(data: Any):
    try:
        if "title" not in data:
            return None, FlaskJSONResponse(content={"error": "title is required"}, status_code=400)
        return data["title"], None
    except Exception:
        return None, _server_error_response()


@app.api_route("/tasks", methods=["GET", "POST"])
async def tasks(request: Request):
    if request.method == "GET":
        return FlaskJSONResponse(content={"tasks": list(_TASKS.values())})

    if request.method == "POST":
        data = (await _get_json_silent(request)) or {}
        title, error_response = _extract_title_or_error(data)
        if error_response is not None:
            return error_response
        return FlaskJSONResponse(content={"id": 2, "title": title, "done": False}, status_code=201)

    return HTMLResponse(content=_HTML_ERROR_BODIES[405], status_code=405)


@app.api_route("/tasks/{task_id:int}", methods=["GET", "PUT", "DELETE"])
async def task(request: Request, task_id: int):
    if request.method == "GET":
        existing = _TASKS.get(task_id)
        if existing is None:
            return FlaskJSONResponse(content={"error": "task not found"}, status_code=404)
        return FlaskJSONResponse(content=existing)

    if request.method == "PUT":
        existing = _TASKS.get(task_id)
        if existing is None:
            return FlaskJSONResponse(content={"error": "task not found"}, status_code=404)
        data = (await _get_json_silent(request)) or {}
        title, error_response = _extract_title_or_error(data)
        if error_response is not None:
            return error_response
        return FlaskJSONResponse(content={**existing, "title": title})

    if request.method == "DELETE":
        if task_id not in _TASKS:
            return FlaskJSONResponse(content={"error": "task not found"}, status_code=404)
        return FlaskJSONResponse(content={"deleted": task_id})

    return HTMLResponse(content=_HTML_ERROR_BODIES[405], status_code=405)