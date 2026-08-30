from fastapi import FastAPI
from fastapi.responses import JSONResponse
from uuid import UUID

app = FastAPI()

_ORGS = {"acme": {"name": "acme", "plan": "pro"}}
_REPOS = {("acme", 7): {"id": 7, "org": "acme", "name": "api"}}
_FILES = {"src/main.py": "print('hi')\n"}


@app.get("/orgs/{org_slug}")
def get_org(org_slug: str):
    org = _ORGS.get(org_slug)
    if org is None:
        return JSONResponse(content={"error": "org not found", "slug": org_slug}, status_code=404)
    return org


@app.get("/orgs/{org_slug}/repos/{repo_id}")
def get_repo(org_slug: str, repo_id: int):
    if org_slug not in _ORGS:
        return JSONResponse(content={"error": "org not found", "slug": org_slug}, status_code=404)
    repo = _REPOS.get((org_slug, repo_id))
    if repo is None:
        return JSONResponse(content={"error": "repo not found", "id": repo_id}, status_code=404)
    return repo


@app.get("/files/{file_path:path}")
def get_file(file_path: str):
    content = _FILES.get(file_path)
    if content is None:
        return JSONResponse(content={"error": "file not found", "path": file_path}, status_code=404)
    return {"path": file_path, "bytes": len(content)}


@app.get("/traces/{trace_id}")
def get_trace(trace_id: UUID):
    return JSONResponse(content={"trace": str(trace_id), "found": False}, status_code=404)