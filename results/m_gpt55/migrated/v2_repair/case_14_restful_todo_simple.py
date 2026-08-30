import json
from email import policy
from email.parser import BytesParser
from http import HTTPStatus
from typing import Optional
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


app = FastAPI()

todos = {}

_BAD_REQUEST_MESSAGE = "The browser (or proxy) sent a request that this server could not understand."
_NOT_FOUND_HTML = """<!doctype html>\n<html lang=en>\n<title>404 Not Found</title>\n<h1>Not Found</h1>\n<p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.</p>\n"""


class FlaskRestfulJSONResponse(JSONResponse):
    media_type = "application/json"

    def render(self, content) -> bytes:
        return (json.dumps(content) + "\n").encode("utf-8")


def _json_response(content, status_code: int = 200, headers: Optional[dict] = None) -> FlaskRestfulJSONResponse:
    return FlaskRestfulJSONResponse(content=content, status_code=status_code, headers=headers)


def _first_urlencoded_value(body: bytes, name: str) -> Optional[str]:
    parsed = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)
    values = parsed.get(name)
    if not values:
        return None
    return values[0]


def _first_multipart_value(body: bytes, content_type: str, name: str) -> Optional[str]:
    try:
        raw_message = (
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
        )
        message = BytesParser(policy=policy.default).parsebytes(raw_message)
        if not message.is_multipart():
            return None

        for part in message.iter_parts():
            params_list = part.get_params(header="content-disposition", unquote=True) or []
            if not params_list:
                continue
            disposition = (params_list[0][0] or "").lower()
            params = {k.lower(): v for k, v in params_list[1:]}
            if disposition == "form-data" and params.get("name") == name and "filename" not in params:
                value = part.get_content()
                if isinstance(value, bytes):
                    return value.decode("utf-8", errors="replace")
                return value
    except Exception:
        return None
    return None


async def _request_form_data_value(request: Request) -> Optional[str]:
    content_type = request.headers.get("content-type", "")
    media_type = content_type.split(";", 1)[0].strip().lower()
    body = await request.body()

    if media_type == "application/x-www-form-urlencoded":
        return _first_urlencoded_value(body, "data")
    if media_type == "multipart/form-data":
        return _first_multipart_value(body, content_type, "data")
    return None


@app.get("/{todo_id}")
async def get_todo(todo_id: str):
    try:
        return _json_response({todo_id: todos[todo_id]})
    except KeyError:
        return _json_response({"message": "Internal Server Error"}, status_code=500)


@app.put("/{todo_id}")
async def put_todo(todo_id: str, request: Request):
    value = await _request_form_data_value(request)
    if value is None:
        return _json_response({"message": _BAD_REQUEST_MESSAGE}, status_code=400)

    todos[todo_id] = value
    return _json_response({todo_id: todos[todo_id]})


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return HTMLResponse(content=_NOT_FOUND_HTML, status_code=404)
    if exc.status_code == 405:
        return _json_response(
            {"message": "The method is not allowed for the requested URL."},
            status_code=405,
            headers=exc.headers,
        )
    message = HTTPStatus(exc.status_code).phrase if exc.status_code in HTTPStatus._value2member_map_ else str(exc.detail)
    return _json_response({"message": message}, status_code=exc.status_code, headers=exc.headers)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return _json_response({"message": "Internal Server Error"}, status_code=500)