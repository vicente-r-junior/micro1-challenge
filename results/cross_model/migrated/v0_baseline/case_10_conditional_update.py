from typing import Optional

from fastapi import Body, FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

app = FastAPI()

_DOCS = {"d1": {"id": "d1", "title": "spec", "version": 3}}


class PatchPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: Optional[str] = None


@app.get("/docs/{doc_id}")
def get_doc(doc_id: str, response: Response):
    doc = _DOCS.get(doc_id)
    if doc is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "doc not found"},
        )
    response.headers["ETag"] = f'W/"{doc["version"]}"'
    return doc


@app.patch("/docs/{doc_id}")
def patch_doc(
    doc_id: str,
    request: Request,
    response: Response,
    payload: Optional[PatchPayload] = Body(default=None),
):
    doc = _DOCS.get(doc_id)
    if doc is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "doc not found"},
        )

    if_match = request.headers.get("If-Match")
    if not if_match:
        return JSONResponse(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            content={
                "error": "If-Match header is required",
                "code": "PRECONDITION_REQUIRED",
            },
        )
    if if_match != f'W/"{doc["version"]}"':
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": "version conflict", "expected": doc["version"]},
        )

    if payload is None or not isinstance(payload.title, str) or not payload.title:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "title must be a non-empty string"},
        )

    title = payload.title
    new_version = doc["version"] + 1
    response.headers["ETag"] = f'W/"{new_version}"'
    return {**doc, "title": title, "version": new_version}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)