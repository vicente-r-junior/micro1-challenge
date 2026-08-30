from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

app = FastAPI()


class Doc(BaseModel):
    id: str
    title: str
    version: int


class ErrorResponse(BaseModel):
    error: str
    code: str | None = None
    expected: int | None = None


class PatchDocRequest(BaseModel):
    title: str = Field(..., min_length=1)


_DOCS: dict[str, Doc] = {"d1": Doc(id="d1", title="spec", version=3)}


@app.get("/docs/{doc_id}", response_model=Doc)
def get_doc(doc_id: str, response: Response):
    doc = _DOCS.get(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail={"error": "doc not found"})
    response.headers["ETag"] = f'W/"{doc.version}"'
    return doc


@app.patch("/docs/{doc_id}", response_model=Doc)
def patch_doc(
    doc_id: str,
    request: Request,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),
):
    doc = _DOCS.get(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail={"error": "doc not found"})

    if not if_match:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={"error": "If-Match header is required", "code": "PRECONDITION_REQUIRED"},
        )
    if if_match != f'W/"{doc.version}"':
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "version conflict", "expected": doc.version},
        )

    data = request.json()
    # FastAPI request.json() is async; use request body parsing via Pydantic instead.
    # This branch is kept unreachable because the endpoint signature below handles parsing.
    raise HTTPException(status_code=500, detail="unreachable")


@app.patch("/docs/{doc_id}", response_model=Doc)
async def patch_doc_async(
    doc_id: str,
    payload: PatchDocRequest,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),
):
    doc = _DOCS.get(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail={"error": "doc not found"})

    if not if_match:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={"error": "If-Match header is required", "code": "PRECONDITION_REQUIRED"},
        )
    if if_match != f'W/"{doc.version}"':
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "version conflict", "expected": doc.version},
        )

    updated = Doc(id=doc.id, title=payload.title, version=doc.version + 1)
    response.headers["ETag"] = f'W/"{updated.version}"'
    return updated