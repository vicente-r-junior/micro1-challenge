"""Pagination advertised through response headers. Synthetic case.

FastAPI migration of the legacy Flask module.
"""

import json
from typing import Any
from urllib.parse import parse_qsl

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)

_EVENTS = [{"id": i, "kind": "click"} for i in range(1, 26)]
MAX_PER_PAGE = 10


class FlaskJSONResponse(JSONResponse):
    """Render JSON like Flask's jsonify in a default non-debug app."""

    def render(self, content: Any) -> bytes:
        return (
            json.dumps(
                content,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")


def _query_pairs(request: Request) -> list[tuple[str, str]]:
    raw_query = request.scope.get("query_string", b"")
    query = raw_query.decode("latin-1")
    return parse_qsl(query, keep_blank_values=True, encoding="utf-8", errors="replace")


def _get_int_arg(request: Request, name: str, default: int) -> int:
    # Werkzeug/Flask's request.args.get(..., type=int) uses the first value and
    # returns the default when conversion fails.
    for key, value in _query_pairs(request):
        if key == name:
            try:
                return int(value)
            except (TypeError, ValueError):
                return default
    return default


_FLASK_500_BODY = """<!doctype html>
<html lang=en>
<title>500 Internal Server Error</title>
<h1>Internal Server Error</h1>
<p>The server encountered an internal error and was unable to complete your request. Either the server is overloaded or there is an error in the application.</p>
"""

_FLASK_404_BODY = """<!doctype html>
<html lang=en>
<title>404 Not Found</title>
<h1>Not Found</h1>
<p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.</p>
"""

_FLASK_405_BODY = """<!doctype html>
<html lang=en>
<title>405 Method Not Allowed</title>
<h1>Method Not Allowed</h1>
<p>The method is not allowed for the requested URL.</p>
"""


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return HTMLResponse(content=_FLASK_404_BODY, status_code=404)
    if exc.status_code == 405:
        headers = getattr(exc, "headers", None)
        return HTMLResponse(content=_FLASK_405_BODY, status_code=405, headers=headers)
    return HTMLResponse(content=str(exc.detail), status_code=exc.status_code, headers=getattr(exc, "headers", None))


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return HTMLResponse(content=_FLASK_500_BODY, status_code=500)


@app.get("/events")
async def events(request: Request):
    page = _get_int_arg(request, "page", 1)
    per_page = _get_int_arg(request, "per_page", 5)

    if page < 1:
        return FlaskJSONResponse(content={"error": "page must be >= 1"}, status_code=400)
    if per_page > MAX_PER_PAGE:
        per_page = MAX_PER_PAGE

    start = (page - 1) * per_page
    rows = _EVENTS[start : start + per_page]
    total = len(_EVENTS)

    if per_page == 0:
        return HTMLResponse(content=_FLASK_500_BODY, status_code=500)

    last_page = (total + per_page - 1) // per_page

    links = [
        f'</events?page=1&per_page={per_page}>; rel="first"',
        f'</events?page={last_page}&per_page={per_page}>; rel="last"',
    ]
    if page < last_page:
        links.append(f'</events?page={page + 1}&per_page={per_page}>; rel="next"')

    headers = {
        "X-Total-Count": str(total),
        "Link": ", ".join(links),
    }
    return FlaskJSONResponse(
        content={"events": rows, "page": page, "per_page": per_page},
        status_code=200,
        headers=headers,
    )