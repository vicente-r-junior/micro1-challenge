from typing import Any

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

app = FastAPI()


class Doc(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    version: int


_DOCS: dict[str, dict[str, Any]] = {"d1": {"id": "d1", "title": "spec", "version": 3}}


def _etag(version: int) -> str:
    return f'W/"{version}"'


@app.get("/docs/{doc_id}")
def get_doc(doc_id: str) -> JSONResponse:
    doc = _DOCS.get(doc_id)
    if doc is None:
        return JSONResponse(content={"error": "doc not found"}, status_code=404)

    validated_doc = Doc.model_validate(doc)
    return JSONResponse(
        content=validated_doc.model_dump(),
        status_code=200,
        headers={"ETag": _etag(validated_doc.version)},
    )


@app.patch("/docs/{doc_id}")
async def patch_doc(
    doc_id: str,
    request: Request,
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> JSONResponse:
    doc = _DOCS.get(doc_id)
    if doc is None:
        return JSONResponse(content={"error": "doc not found"}, status_code=404)

    current_doc = Doc.model_validate(doc)

    if not if_match:
        return JSONResponse(
            content={"error": "If-Match header is required", "code": "PRECONDITION_REQUIRED"},
            status_code=428,
        )

    if if_match != _etag(current_doc.version):
        return JSONResponse(
            content={"error": "version conflict", "expected": current_doc.version},
            status_code=409,
        )

    try:
        data = await request.json()
    except Exception:
        data = {}

    if not isinstance(data, dict):
        data = {}

    title = data.get("title")
    if not isinstance(title, str) or not title:
        return JSONResponse(content={"error": "title must be a non-empty string"}, status_code=400)

    updated_doc = Doc.model_validate({**doc, "title": title, "version": current_doc.version + 1})
    return JSONResponse(
        content=updated_doc.model_dump(),
        status_code=200,
        headers={"ETag": _etag(updated_doc.version)},
    )