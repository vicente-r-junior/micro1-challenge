from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.router.redirect_slashes = False

TODOS = {
    "todo1": {"task": "build an API"},
    "todo2": {"task": "?????"},
    "todo3": {"task": "profit!"},
}


class ParsedArgs(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    task: Any = None


class FlaskRestfulJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return (json.dumps(content) + "\n").encode("utf-8")


def jsonify_flask_restful(content: Any, status_code: int = 200, headers: dict[str, str] | None = None) -> JSONResponse:
    return FlaskRestfulJSONResponse(content=content, status_code=status_code, headers=headers)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if exc.status_code == 405:
        return jsonify_flask_restful(
            {"message": "The method is not allowed for the requested URL."},
            status_code=405,
            headers=exc.headers,
        )
    return jsonify_flask_restful({"message": exc.detail}, status_code=exc.status_code, headers=exc.headers)


def abort_if_todo_doesnt_exist(todo_id: str) -> JSONResponse | None:
    if todo_id not in TODOS:
        return jsonify_flask_restful(
            {"message": "Todo {} doesn't exist".format(todo_id)},
            status_code=404,
        )
    return None


def _is_json_content_type(content_type: str | None) -> bool:
    if not content_type:
        return False
    mimetype = content_type.split(";", 1)[0].strip().lower()
    return mimetype == "application/json" or mimetype.endswith("+json")


def _is_form_content_type(content_type: str | None) -> bool:
    if not content_type:
        return False
    mimetype = content_type.split(";", 1)[0].strip().lower()
    return mimetype == "application/x-www-form-urlencoded"


def _first_reqparse_value(value: Any) -> Any:
    if isinstance(value, list):
        if not value:
            return None
        return value[0]
    return value


def _coerce_reqparse_string(value: Any) -> Any:
    if value is None:
        return None
    return str(value)


def _extract_task_from_json_payload(payload: Any) -> tuple[bool, Any]:
    if payload is None:
        return False, None

    if isinstance(payload, dict):
        if "task" not in payload:
            return False, None
        return True, _first_reqparse_value(payload.get("task"))

    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, (list, tuple)) and len(item) == 2 and item[0] == "task":
                return True, _first_reqparse_value(item[1])

    return False, None


async def parse_args(request: Request) -> ParsedArgs | JSONResponse:
    content_type = request.headers.get("content-type")
    body = await request.body()

    if _is_json_content_type(content_type):
        try:
            payload = json.loads(body)
        except Exception:
            return jsonify_flask_restful(
                {"message": "The browser (or proxy) sent a request that this server could not understand."},
                status_code=400,
            )

        found, value = _extract_task_from_json_payload(payload)
        if found:
            return ParsedArgs(task=_coerce_reqparse_string(value))

    if "task" in request.query_params:
        return ParsedArgs(task=request.query_params.getlist("task")[0])

    if _is_form_content_type(content_type):
        parsed_form = parse_qs(
            body.decode("utf-8", errors="replace"),
            keep_blank_values=True,
            encoding="utf-8",
            errors="replace",
        )
        if "task" in parsed_form and parsed_form["task"]:
            return ParsedArgs(task=parsed_form["task"][0])

    return ParsedArgs(task=None)


@app.get("/todos")
async def todo_list_get() -> JSONResponse:
    return jsonify_flask_restful(TODOS)


@app.post("/todos")
async def todo_list_post(request: Request) -> JSONResponse:
    args = await parse_args(request)
    if isinstance(args, JSONResponse):
        return args

    todo_id = "todo%d" % (len(TODOS) + 1)
    TODOS[todo_id] = {"task": args.task}
    return jsonify_flask_restful(TODOS[todo_id], status_code=201)


@app.get("/todos/{todo_id}")
async def todo_get(todo_id: str) -> JSONResponse:
    error = abort_if_todo_doesnt_exist(todo_id)
    if error is not None:
        return error
    return jsonify_flask_restful(TODOS[todo_id])


@app.delete("/todos/{todo_id}", response_model=None)
async def todo_delete(todo_id: str):
    error = abort_if_todo_doesnt_exist(todo_id)
    if error is not None:
        return error
    del TODOS[todo_id]
    return Response(content=b"", status_code=204, media_type="application/json")


@app.put("/todos/{todo_id}")
async def todo_put(todo_id: str, request: Request) -> JSONResponse:
    args = await parse_args(request)
    if isinstance(args, JSONResponse):
        return args

    task = {"task": args.task}
    TODOS[todo_id] = task
    return jsonify_flask_restful(task, status_code=201)
