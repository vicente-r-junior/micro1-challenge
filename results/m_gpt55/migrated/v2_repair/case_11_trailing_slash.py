"""FastAPI migration of the legacy Flask trailing-slash behaviour example."""

import json
from html import escape
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from fastapi import FastAPI, Request
from fastapi.responses import Response
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.router.redirect_slashes = False


def flask_jsonify(content: Any, status_code: int = 200) -> Response:
    body = json.dumps(
        content,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    return Response(content=body, status_code=status_code, media_type="application/json")


def flask_html_error(status_code: int, title: str, heading: str, message: str, headers: dict[str, str] | None = None) -> Response:
    body = (
        "<!doctype html>\n"
        "<html lang=en>\n"
        f"<title>{status_code} {title}</title>\n"
        f"<h1>{heading}</h1>\n"
        f"<p>{message}</p>\n"
    )
    return Response(
        content=body,
        status_code=status_code,
        media_type="text/html; charset=utf-8",
        headers=headers,
    )


def flask_redirect(location: str, status_code: int = 308) -> Response:
    escaped_location = escape(location)
    body = (
        "<!doctype html>\n"
        "<html lang=en>\n"
        "<title>Redirecting...</title>\n"
        "<h1>Redirecting...</h1>\n"
        "<p>You should be redirected automatically to the target URL: "
        f"<a href=\"{escaped_location}\">{escaped_location}</a>. If not, click the link.\n"
    )
    return Response(
        content=body,
        status_code=status_code,
        media_type="text/html; charset=utf-8",
        headers={"Location": location},
    )


def add_trailing_slash_to_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path + "/", parts.query, parts.fragment))


@app.middleware("http")
async def preserve_flask_slash_semantics(request: Request, call_next):
    # Flask strict_slashes redirects /reports -> /reports/ with status 308.
    if request.method == "GET" and request.url.path == "/reports":
        return flask_redirect(add_trailing_slash_to_url(str(request.url)), status_code=308)

    # The legacy /jobs route was declared strict_slashes=False, so /jobs/ is accepted too.
    if request.method == "GET" and request.url.path == "/jobs/":
        return flask_jsonify({"jobs": []})

    return await call_next(request)


@app.exception_handler(StarletteHTTPException)
async def preserve_flask_http_errors(request: Request, exc: StarletteHTTPException) -> Response:
    if exc.status_code == 404:
        return flask_html_error(
            404,
            "Not Found",
            "Not Found",
            "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.",
        )
    if exc.status_code == 405:
        return flask_html_error(
            405,
            "Method Not Allowed",
            "Method Not Allowed",
            "The method is not allowed for the requested URL.",
            headers=dict(exc.headers or {}),
        )
    return flask_html_error(
        exc.status_code,
        str(exc.detail),
        str(exc.detail),
        str(exc.detail),
        headers=dict(exc.headers or {}),
    )


@app.get("/reports/")
def list_reports() -> Response:
    return flask_jsonify({"reports": ["daily", "weekly"]})


@app.get("/status")
def status() -> Response:
    return flask_jsonify({"status": "up"})


@app.get("/jobs")
def jobs() -> Response:
    return flask_jsonify({"jobs": []})


@app.get("/queue/{name}")
def queue(name: str) -> Response:
    return flask_jsonify({"queue": name, "depth": 0})