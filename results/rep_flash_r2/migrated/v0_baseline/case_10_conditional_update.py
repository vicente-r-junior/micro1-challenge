"""Optimistic concurrency with a version header. FastAPI migration."""
from typing import Optional

import uvicorn
from fastapi import Body, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI()

_DOCS = {"d1": {"id": "d1", "title": "spec", "version": 3}}


class DocPatch(BaseModel):
    title: str = Field(min_length=1)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        {"error": "title must be a non-empty string"},
        status_code=400,
    )


@app.get("/docs/{doc_id}")
def get_doc(doc_id: str):
    doc = _DOCS.get(doc_id)
    if doc is None:
        return JSONResponse({"error": "doc not found"}, status_code=404)

    response = JSONResponse(doc, status_code=200)
    response.headers["ETag"] = f'W/"{doc["version"]}"'
    return response


@app.patch("/docs/{doc_id}")
def patch_doc(
    doc_id: str,
    payload: Optional[DocPatch] = Body(default=None),
    if_match: Optional[str] = Header(default=None),
):
    doc = _DOCS.get(doc_id)
    if doc is None:
        return JSONResponse({"error": "doc not found"}, status_code=404)

    if if_match is None:
        return JSONResponse(
            {"error": "If-Match header is required", "code": "PRECONDITION_REQUIRED"},
            status_code=428,
        )

    if if_match != f'W/"{doc["version"]}"':
        return JSONResponse(
            {"error": "version conflict", "expected": doc["version"]},
            status_code=409,
        )

    if payload is None:
        return JSONResponse(
            {"error": "title must be a non-empty string"},
            status_code=400,
        )

    new_doc = {
        **doc,
        "title": payload.title,
        "version": doc["version"] + 1,
    }
    _DOCS[doc_id] = new_doc

    response = JSONResponse(new_doc, status_code=200)
    response.headers["ETag"] = f'W/"{new_doc["version"]}"'
    return response


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)