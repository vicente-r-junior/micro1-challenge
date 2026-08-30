"""Optimistic concurrency with a version header. Synthetic case.

Exercises: a request header that drives control flow, PATCH semantics, 409 on a
version mismatch, 428 when the header is absent, and a response header echoing
 the new version.
"""

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

_DOCS = {"d1": {"id": "d1", "title": "spec", "version": 3}}

class PatchDocRequest(BaseModel):
    title: Optional[str] = None

@app.get("/docs/{doc_id}")
async def get_doc(doc_id: str):
    doc = _DOCS.get(doc_id)
    if doc is None:
        return JSONResponse(content={"error": "doc not found"}, status_code=404)
    response = JSONResponse(content=doc, status_code=200)
    response.headers["ETag"] = f'W/"{doc["version"]}"'
    return response

@app.patch("/docs/{doc_id}")
async def patch_doc(doc_id: str, if_match: Optional[str] = Header(None), request_body: PatchDocRequest = None):
    doc = _DOCS.get(doc_id)
    if doc is None:
        return JSONResponse(content={"error": "doc not found"}, status_code=404)

    if if_match is None:
        return JSONResponse(content={"error": "If-Match header is required", "code": "PRECONDITION_REQUIRED"}, status_code=428)
    if if_match != f'W/"{doc["version"]}"':
        return JSONResponse(content={"error": "version conflict", "expected": doc["version"]}, status_code=409)

    title = request_body.title if request_body else None
    if not isinstance(title, str) or not title:
        return JSONResponse(content={"error": "title must be a non-empty string"}, status_code=400)

    updated_doc = {**doc, "title": title, "version": doc["version"] + 1}
    response = JSONResponse(content=updated_doc, status_code=200)
    response.headers["ETag"] = f'W/"{updated_doc["version"]}"'
    return response