import json
import uuid

from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

FLASK_404_HTML = (
    "<!doctype html>\n"
    "<html lang=en>\n"
    "<title>404 Not Found</title>\n"
    "<h1>Not Found</h1>\n"
    "<p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.</p>\n"
)

FLASK_405_HTML = (
    "<!doctype html>\n"
    "<html lang=en>\n"
    "<title>405 Method Not Allowed</title>\n"
    "<h1>Method Not Allowed</h1>\n"
    "<p>The method is not allowed for the requested URL.</p>\n"
)

app = FastAPI()

_ORGS = {"acme": {"name": "acme", "plan": "pro"}}
_REPOS = {("acme", 7): {"id": 7, "org": "acme", "name": "api"}}
_FILES = {"src/main.py": "print('hi')\n"}


def json_response(data, status_code=200):
    body = json.dumps(data, sort_keys=True, separators=(", ", ": "))
    return Response(
        content=body,
        status_code=status_code,
        media_type="application/json",
        headers={"Content-Type": "application/json"},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    if exc.status_code == 404:
        return HTMLResponse(content=FLASK_404_HTML, status_code=404)
    if exc.status_code == 405:
        return HTMLResponse(content=FLASK_405_HTML, status_code=405)
    return json_response({"detail": exc.detail}, status_code=exc.status_code)


@app.get("/orgs/{org_slug}")
def get_org(org_slug: str):
    org = _ORGS.get(org_slug)
    if org is None:
        return json_response({"error": "org not found", "slug": org_slug}, status_code=404)
    return json_response(org)


@app.get("/orgs/{org_slug}/repos/{repo_id:int}")
def get_repo(org_slug: str, repo_id: int):
    if org_slug not in _ORGS:
        return json_response({"error": "org not found", "slug": org_slug}, status_code=404)
    repo = _REPOS.get((org_slug, repo_id))
    if repo is None:
        return json_response({"error": "repo not found", "id": repo_id}, status_code=404)
    return json_response(repo)


@app.get("/files/{file_path:path}")
def get_file(file_path: str):
    if file_path == "" or file_path.startswith("/"):
        return HTMLResponse(content=FLASK_404_HTML, status_code=404)
    content = _FILES.get(file_path)
    if content is None:
        return json_response({"error": "file not found", "path": file_path}, status_code=404)
    return json_response({"path": file_path, "bytes": len(content)})


@app.get("/traces/{trace_id:uuid}")
def get_trace(trace_id: uuid.UUID):
    return json_response({"trace": str(trace_id), "found": False}, status_code=404)