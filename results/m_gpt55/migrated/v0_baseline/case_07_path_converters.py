from uuid import UUID

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()


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


class TraceResult(BaseModel):
    trace: str
    found: bool


_ORGS: dict[str, dict[str, str]] = {"acme": {"name": "acme", "plan": "pro"}}
_REPOS: dict[tuple[str, int], dict[str, int | str]] = {
    ("acme", 7): {"id": 7, "org": "acme", "name": "api"}
}
_FILES: dict[str, str] = {"src/main.py": "print('hi')\n"}


@app.get("/orgs/{org_slug}", response_model=Org)
def get_org(org_slug: str):
    org = _ORGS.get(org_slug)
    if org is None:
        return JSONResponse(
            status_code=404,
            content={"error": "org not found", "slug": org_slug},
        )
    return org


@app.get("/orgs/{org_slug}/repos/{repo_id:int}", response_model=Repo)
def get_repo(org_slug: str, repo_id: int):
    if org_slug not in _ORGS:
        return JSONResponse(
            status_code=404,
            content={"error": "org not found", "slug": org_slug},
        )
    repo = _REPOS.get((org_slug, repo_id))
    if repo is None:
        return JSONResponse(
            status_code=404,
            content={"error": "repo not found", "id": repo_id},
        )
    return repo


@app.get("/files/{file_path:path}", response_model=FileInfo)
def get_file(file_path: str):
    content = _FILES.get(file_path)
    if content is None:
        return JSONResponse(
            status_code=404,
            content={"error": "file not found", "path": file_path},
        )
    return {"path": file_path, "bytes": len(content)}


@app.get("/traces/{trace_id:uuid}", response_model=TraceResult)
def get_trace(trace_id: UUID):
    return JSONResponse(
        status_code=404,
        content={"trace": str(trace_id), "found": False},
    )