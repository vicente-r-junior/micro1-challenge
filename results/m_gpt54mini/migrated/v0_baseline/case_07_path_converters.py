from fastapi import FastAPI, HTTPException
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
        raise HTTPException(status_code=404, detail={"error": "org not found", "slug": org_slug})
    return org


@app.get("/orgs/{org_slug}/repos/{repo_id}")
def get_repo(org_slug: str, repo_id: int):
    if org_slug not in _ORGS:
        raise HTTPException(status_code=404, detail={"error": "org not found", "slug": org_slug})
    repo = _REPOS.get((org_slug, repo_id))
    if repo is None:
        raise HTTPException(status_code=404, detail={"error": "repo not found", "id": repo_id})
    return repo


@app.get("/files/{file_path:path}")
def get_file(file_path: str):
    content = _FILES.get(file_path)
    if content is None:
        raise HTTPException(status_code=404, detail={"error": "file not found", "path": file_path})
    return {"path": file_path, "bytes": len(content)}


@app.get("/traces/{trace_id}")
def get_trace(trace_id: UUID):
    return JSONResponse(status_code=404, content={"trace": str(trace_id), "found": False})