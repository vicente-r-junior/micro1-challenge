import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

_DOCS = {"d1": {"id": "d1", "title": "spec", "version": 3}}

def _etag(version: int) -> str:
    return f'W/"{version}"'

@app.get("/docs/{doc_id}")
async def get_doc(doc_id: str):
    doc = _DOCS.get(doc_id)
    if doc is None:
        return JSONResponse(status_code=404, content={"error": "doc not found"})
    return JSONResponse(status_code=200, content=doc, headers={"ETag": _etag(doc["version"])})

@app.patch("/docs/{doc_id}")
async def patch_doc(doc_id: str, request: Request):
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

    body = await request.body()
    data = {}
    if body:
        content_type = request.headers.get("content-type")
        if content_type:
            mimetype = content_type.split(";")[0].strip().lower()
            if mimetype == "application/json" or mimetype.endswith("+json"):
                try:
                    parsed = json.loads(body)
                    if isinstance(parsed, dict):
                        data = parsed
                except Exception:
                    data = {}

    title = data.get("title")
    if not isinstance(title, str) or not title:
        return JSONResponse(
            status_code=400,
            content={"error": "title must be a non-empty string"},
        )

    new_version = doc["version"] + 1
    updated_doc = {**doc, "title": title, "version": new_version}
    return JSONResponse(
        status_code=200,
        content=updated_doc,
        headers={"ETag": _etag(new_version)},
    )