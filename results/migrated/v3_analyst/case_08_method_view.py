import json
import re
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

_TASKS = {1: {"id": 1, "title": "write migration", "done": False}}

_INT_RE = re.compile(r"\d+")

_FLASK_404_BODY = (
    '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n'
    '<title>404 Not Found</title>\n'
    '<h1>Not Found</h1>\n'
    '<p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.</p>\n'
)

_FLASK_405_BODY = (
    '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n'
    '<title>405 Method Not Allowed</title>\n'
    '<h1>Method Not Allowed</h1>\n'
    '<p>The method is not allowed for the requested URL.</p>\n'
)


class FlaskJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=True,
            allow_nan=True,
            indent=None,
            separators=(", ", ": "),
        ).encode("utf-8")


def _is_json_request(request: Request) -> bool:
    content_type = request.headers.get("content-type", "")
    if not content_type:
        return False
    mimetype = content_type.split(";", 1)[0].strip().lower()
    if mimetype == "application/json":
        return True
    return mimetype.startswith("application/") and mimetype.endswith("+json")


async def _read_json_body(request: Request):
    if not _is_json_request(request):
        return {}
    try:
        data = await request.json()
    except Exception:
        return {}
    if not data:
        return {}
    return data


def _parse_task_id(task_id: str):
    if _INT_RE.fullmatch(task_id) is None:
        return None
    return int(task_id)


def _flask_404() -> HTMLResponse:
    return HTMLResponse(_FLASK_404_BODY, status_code=404)


@app.middleware("http")
async def _flask_int_converter_middleware(request: Request, call_next):
    path = request.url.path
    parts = path.split("/")
    if len(parts) == 3 and parts[1] == "tasks" and parts[2] and _INT_RE.fullmatch(parts[2]) is None:
        return _flask_404()
    return await call_next(request)


def _path_is_non_integer_task_id(path: str) -> bool:
    parts = path.split("/")
    if len(parts) != 3:
        return False
    if parts[1] != "tasks":
        return False
    return _INT_RE.fullmatch(parts[2]) is None


@app.exception_handler(StarletteHTTPException)
async def _http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return _flask_404()
    if exc.status_code == 405:
        if _path_is_non_integer_task_id(request.url.path):
            return _flask_404()
        allow = (exc.headers or {}).get("Allow", "")
        methods = [m.strip().upper() for m in allow.split(",") if m.strip()]
        if "GET" in methods and "HEAD" not in methods:
            methods.append("HEAD")
        if "OPTIONS" not in methods:
            methods.append("OPTIONS")
        headers = {"Allow": ", ".join(sorted(methods))}
        return HTMLResponse(_FLASK_405_BODY, status_code=405, headers=headers)
    return FlaskJSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=dict(exc.headers or {}))


@app.get("/tasks")
async def list_tasks():
    return FlaskJSONResponse({"tasks": list(_TASKS.values())})


@app.post("/tasks")
async def create_task(request: Request):
    data = await _read_json_body(request)
    if "title" not in data:
        return FlaskJSONResponse({"error": "title is required"}, status_code=400)
    return FlaskJSONResponse({"id": 2, "title": data["title"], "done": False}, status_code=201)


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    parsed = _parse_task_id(task_id)
    if parsed is None:
        return _flask_404()
    task = _TASKS.get(parsed)
    if task is None:
        return FlaskJSONResponse({"error": "task not found"}, status_code=404)
    return FlaskJSONResponse(task)


@app.put("/tasks/{task_id}")
async def put_task(task_id: str, request: Request):
    parsed = _parse_task_id(task_id)
    if parsed is None:
        return _flask_404()
    task = _TASKS.get(parsed)
    if task is None:
        return FlaskJSONResponse({"error": "task not found"}, status_code=404)
    data = await _read_json_body(request)
    if "title" not in data:
        return FlaskJSONResponse({"error": "title is required"}, status_code=400)
    return FlaskJSONResponse({**task, "title": data["title"]})


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    parsed = _parse_task_id(task_id)
    if parsed is None:
        return _flask_404()
    if parsed not in _TASKS:
        return FlaskJSONResponse({"error": "task not found"}, status_code=404)
    return FlaskJSONResponse({"deleted": parsed})