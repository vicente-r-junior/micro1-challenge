"""Nested resources with several path converters. Synthetic FastAPI case.

Exercises: string, int, uuid and path converters, a route whose parameter can
contain slashes, and a sub-resource that 404s independently of its parent.
"""

from uuid import UUID

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

_ORGS = {"acme": {"name": "acme", "plan": "pro"}}
_REPOS = {("acme", 7): {"id": 7, "org": "acme", "name": "api"}}
_FILES = {"src/main.py": "print('hi')\n"}


class Org(BaseModel):
    name: str
    plan: str


class Repo(BaseModel):
    id: int
    org: str
    name: str


class FileInfo(BaseModel):
    path: str
    bytes: int


@app.get("/orgs/{org_slug}", response_model=Org)
def get_org(org_slug: str):
    org = _ORGS.get(org_slug)
    if org is None:
        return JSONResponse({"error": "org not found", "slug": org_slug}, status_code=404)
    return org


@app.get("/orgs/{org_slug}/repos/{repo_id}", response_model=Repo)
def get_repo(org_slug: str, repo_id: int):
    if org_slug not in _ORGS:
        return JSONResponse({"error": "org not found", "slug": org_slug}, status_code=404)
    repo = _REPOS.get((org_slug, repo_id))
    if repo is None:
        return JSONResponse({"error": "repo not found", "id": repo_id}, status_code=404)
    return repo


@app.get("/files/{file_path:path}", response_model=FileInfo)
def get_file(file_path: str):
    content = _FILES.get(file_path)
    if content is None:
        return JSONResponse({"error": "file not found", "path": file_path}, status_code=404)
    return {"path": file_path, "bytes": len(content)}


@app.get("/traces/{trace_id}")
def get_trace(trace_id: UUID):
    return JSONResponse({"trace": str(trace_id), "found": False}, status_code=404)