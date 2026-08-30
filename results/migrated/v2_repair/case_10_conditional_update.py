"""Optimistic concurrency with a version header. Synthetic case.

Exercises: a request header that drives control flow, PATCH semantics, 409 on a
version mismatch, 428 when the header is absent, and a response header echoing
the new version.
"""

import json

from fastapi import FastAPI, Request, Response

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

_DOCS = {"d1": {"id": "d1", "title": "spec", "version": 3}}


def _flask_style_json_response(data, status_code=200, headers=None):
    body = json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return Response(content=body, status_code=status_code, media_type="application/json", headers=headers)


@app.get("/docs/{doc_id}")
def get_doc(doc_id: str):
    doc = _DOCS.get(doc_id)
    if doc is None:
        return _flask_style_json_response({"error": "doc not found"}, status_code=404)
    response = _flask_style_json_response(doc, status_code=200)
    response.headers["ETag"] = f'W/"{doc["version"]}"'
    return response


@app.patch("/docs/{doc_id}")
async def patch_doc(doc_id: str, request: Request):
    doc = _DOCS.get(doc_id)
    if doc is None:
        return _flask_style_json_response({"error": "doc not found"}, status_code=404)

    if_match = request.headers.get("If-Match")
    if not if_match:
        return _flask_style_json_response(
            {"error": "If-Match header is required", "code": "PRECONDITION_REQUIRED"},
            status_code=428,
        )
    if if_match != f'W/"{doc["version"]}"':
        return _flask_style_json_response(
            {"error": "version conflict", "expected": doc["version"]},
            status_code=409,
        )

    data = {}
    content_type = request.headers.get("content-type")
    if content_type:
        mimetype = content_type.split(";")[0].strip().lower()
        if mimetype == "application/json" or (
            mimetype.startswith("application/") and mimetype.endswith("+json")
        ):
            raw = await request.body()
            if raw:
                try:
                    parsed = json.loads(raw.decode("utf-8"))
                except Exception:
                    parsed = None
                data = parsed or {}

    title = data.get("title")
    if not isinstance(title, str) or not title:
        return _flask_style_json_response(
            {"error": "title must be a non-empty string"}, status_code=400
        )

    updated = {**doc, "title": title, "version": doc["version"] + 1}
    response = _flask_style_json_response(updated, status_code=200)
    response.headers["ETag"] = f'W/"{doc["version"] + 1}"'
    return response