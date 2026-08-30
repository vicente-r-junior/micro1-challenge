"""Nested resources with several path converters. Synthetic case.

Exercises: string, int, uuid and path converters, a route whose parameter can
contain slashes, and a sub-resource that 404s independently of its parent.
"""

import json
import re
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.router.redirect_slashes = False

_ORGS = {"acme": {"name": "acme", "plan": "pro"}}
_REPOS = {("acme", 7): {"id": 7, "org": "acme", "name": "api"}}
_FILES = {"src/main.py": "print('hi')\n"}

FLASK_404_HTML = """<!doctype html>
<html lang=en>
<title>404 Not Found</title>
<h1>Not Found</h1>
<p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.</p>
"""

FLASK_405_HTML = """<!doctype html>
<html lang=en>
<title>405 Method Not Allowed</title>
<h1>Method Not Allowed</h1>
<p>The method is not allowed for the requested URL.</p>
"""


class FlaskJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=True,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")


def json_response(content, status_code=200):
    return FlaskJSONResponse(content=content, status_code=status_code)


@app.exception_handler(404)
async def flask_404_handler(request: Request, exc: StarletteHTTPException):
    return HTMLResponse(status_code=404, content=FLASK_404_HTML)


@app.exception_handler(405)
async def flask_405_handler(request: Request, exc: StarletteHTTPException):
    return HTMLResponse(status_code=405, content=FLASK_405_HTML)


@app.get("/files/{file_path:path}")
def get_file(file_path: str):
    if file_path == "" or file_path.startswith("/"):
        return HTMLResponse(status_code=404, content=FLASK_404_HTML)
    content = _FILES.get(file_path)
    if content is None:
        return json_response({"error": "file not found", "path": file_path}, 404)
    return json_response({"bytes": len(content), "path": file_path})


@app.get("/orgs/{org_slug}")
def get_org(org_slug: str):
    org = _ORGS.get(org_slug)
    if org is None:
        return json_response({"error": "org not found", "slug": org_slug}, 404)
    return json_response(org)


@app.get("/orgs/{org_slug}/repos/{repo_id}")
def get_repo(org_slug: str, repo_id: str):
    if re.fullmatch(r"[0-9]+", repo_id) is None:
        return HTMLResponse(status_code=404, content=FLASK_404_HTML)
    repo_id = int(repo_id)
    if org_slug not in _ORGS:
        return json_response({"error": "org not found", "slug": org_slug}, 404)
    repo = _REPOS.get((org_slug, repo_id))
    if repo is None:
        return json_response({"error": "repo not found", "id": repo_id}, 404)
    return json_response(repo)


@app.get("/traces/{trace_id}")
def get_trace(trace_id: str):
    if re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", trace_id) is None:
        return HTMLResponse(status_code=404, content=FLASK_404_HTML)
    return json_response({"found": False, "trace": str(uuid.UUID(trace_id))}, 404)