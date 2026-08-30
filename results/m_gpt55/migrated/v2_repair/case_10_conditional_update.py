from typing import Any
import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel


class Settings(BaseModel):
    pass


app = FastAPI()

_DOCS = {"d1": {"id": "d1", "title": "spec", "version": 3}}


def jsonify_response(content: Any, status_code: int = 200, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(content=content, status_code=status_code, headers=headers)


@app.get("/docs/{doc_id}")
def get_doc(doc_id: str):
    doc = _DOCS.get(doc_id)
    if doc is None:
        return jsonify_response({"error": "doc not found"}, 404)
    return jsonify_response(doc, 200, headers={"ETag": f'W/"{doc["version"]}"'})


@app.patch("/docs/{doc_id}")
async def patch_doc(doc_id: str, request: Request):
    doc = _DOCS.get(doc_id)
    if doc is None:
        return jsonify_response({"error": "doc not found"}, 404)

    if_match = request.headers.get("if-match")
    if not if_match:
        return jsonify_response({"error": "If-Match header is required", "code": "PRECONDITION_REQUIRED"}, 428)
    if if_match != f'W/"{doc["version"]}"':
        return jsonify_response({"error": "version conflict", "expected": doc["version"]}, 409)

    data: Any = {}
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type or content_type.endswith("+json"):
        body = await request.body()
        if body:
            try:
                data = json.loads(body)
            except Exception:
                data = {}
        else:
            data = {}
    data = data or {}

    try:
        title = data.get("title")
    except AttributeError:
        return Response(content="Internal Server Error", status_code=500, media_type="text/plain")

    if not isinstance(title, str) or not title:
        return jsonify_response({"error": "title must be a non-empty string"}, 400)

    new_doc = {**doc, "title": title, "version": doc["version"] + 1}
    return jsonify_response(new_doc, 200, headers={"ETag": f'W/"{doc["version"] + 1}"'})