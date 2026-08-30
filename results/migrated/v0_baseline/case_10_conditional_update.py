"""Optimistic concurrency with a version header. Synthetic case.

Exercises: a request header that drives control flow, PATCH semantics, 409 on a
version mismatch, 428 when the header is absent, and a response header echoing
the new version.
"""

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError, field_validator

app = FastAPI()

_DOCS = {"d1": {"id": "d1", "title": "spec", "version": 3}}


def _etag(version: int) -> str:
    return f'W/"{version}"'


class PatchRequest(BaseModel):
    title: str

    @field_validator("title", mode="before")
    @classmethod
    def title_must_be_non_empty_string(cls, v):
        if not isinstance(v, str) or not v:
            raise ValueError("title must be a non-empty string")
        return v


async def _get_json_body(request: Request) -> dict:
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type:
        return {}
    try:
        data = await request.json()
    except Exception:
        data = None
    return data if isinstance(data, dict) else {}


@app.get("/docs/{doc_id}")
def get_doc(doc_id: str, response: Response):
    doc = _DOCS.get(doc_id)
    if doc is None:
        return JSONResponse(status_code=404, content={"error": "doc not found"})
    response.headers["ETag"] = _etag(doc["version"])
    return doc


@app.patch("/docs/{doc_id}")
async def patch_doc(doc_id: str, request: Request, response: Response):
    doc = _DOCS.get(doc_id)
    if doc is None:
        return JSONResponse(status_code=404, content={"error": "doc not found"})

    if_match = request.headers.get("If-Match")
    if not if_match:
        return JSONResponse(
            status_code=428,
            content={"error": "If-Match header is required", "code": "PRECONDITION_REQUIRED"},
        )
    if if_match != _etag(doc["version"]):
        return JSONResponse(
            status_code=409,
            content={"error": "version conflict", "expected": doc["version"]},
        )

    data = await _get_json_body(request)
    try:
        patch_body = PatchRequest.model_validate(data)
    except ValidationError:
        return JSONResponse(
            status_code=400,
            content={"error": "title must be a non-empty string"},
        )

    new_version = doc["version"] + 1
    updated_doc = {**doc, "title": patch_body.title, "version": new_version}
    response.headers["ETag"] = _etag(new_version)
    return updated_doc