"""Nested resources with several path converters. Synthetic case.

FastAPI migration preserving the observable behavior of the legacy Flask app.
"""

import re
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(redirect_slashes=False)

_ORGS = {"acme": {"name": "acme", "plan": "pro"}}
_REPOS = {("acme", 7): {"id": 7, "org": "acme", "name": "api"}}
_FILES = {"src/main.py": "print('hi')\n"}

_UUID_RE = re.compile(
    r"^[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}$"
)


def _flask_default_error_body(status_code: int, name: str, description: str) -> str:
    return (
        "<!doctype html>\n"
        "<html lang=en>\n"
        f"<title>{status_code} {name}</title>\n"
        f"<h1>{name}</h1>\n"
        f"<p>{description}</p>\n"
    )


def _flask_404_response() -> HTMLResponse:
    return HTMLResponse(
        content=_flask_default_error_body(
            404,
            "Not Found",
            "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.",
        ),
        status_code=404,
    )


@app.exception_handler(StarletteHTTPException)
async def flask_like_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return _flask_404_response()
    if exc.status_code == 405:
        return HTMLResponse(
            content=_flask_default_error_body(
                405,
                "Method Not Allowed",
                "The method is not allowed for the requested URL.",
            ),
            status_code=405,
            headers=exc.headers,
        )
    return HTMLResponse(
        content=_flask_default_error_body(exc.status_code, str(exc.detail), str(exc.detail)),
        status_code=exc.status_code,
        headers=exc.headers,
    )


@app.get("/orgs/{org_slug}")
def get_org(org_slug: str):
    org = _ORGS.get(org_slug)
    if org is None:
        return JSONResponse(content={"error": "org not found", "slug": org_slug}, status_code=404)
    return JSONResponse(content=org)


@app.get("/orgs/{org_slug}/repos/{repo_id:int}")
def get_repo(org_slug: str, repo_id: int):
    if org_slug not in _ORGS:
        return JSONResponse(content={"error": "org not found", "slug": org_slug}, status_code=404)
    repo = _REPOS.get((org_slug, repo_id))
    if repo is None:
        return JSONResponse(content={"error": "repo not found", "id": repo_id}, status_code=404)
    return JSONResponse(content=repo)


@app.get("/files/{file_path:path}")
def get_file(file_path: str):
    if file_path == "":
        return _flask_404_response()
    content = _FILES.get(file_path)
    if content is None:
        return JSONResponse(content={"error": "file not found", "path": file_path}, status_code=404)
    return JSONResponse(content={"path": file_path, "bytes": len(content)})


@app.get("/traces/{trace_id}")
def get_trace(trace_id: str):
    if not _UUID_RE.fullmatch(trace_id):
        return _flask_404_response()
    parsed_trace_id = UUID(trace_id)
    return JSONResponse(content={"trace": str(parsed_trace_id), "found": False}, status_code=404)