from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, constr

app = FastAPI()

_DOCS = {"d1": {"id": "d1", "title": "spec", "version": 3}}

class Document(BaseModel):
    id: str
    title: constr(min_length=1)
    version: int

@app.get("/docs/{doc_id}")
async def get_doc(doc_id: str):
    doc = _DOCS.get(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail={"error": "doc not found"})
    response = JSONResponse(content=doc)
    response.headers["ETag"] = f'W/"{doc["version"]}"'
    return response

@app.patch("/docs/{doc_id}")
async def patch_doc(doc_id: str, title: str, if_match: str = Header(None)):
    doc = _DOCS.get(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail={"error": "doc not found"})

    if if_match is None:
        raise HTTPException(status_code=428, detail={"error": "If-Match header is required", "code": "PRECONDITION_REQUIRED"})
    if if_match != f'W/"{doc["version"]}"':
        raise HTTPException(status_code=409, detail={"error": "version conflict", "expected": doc["version"]})

    response = JSONResponse(content={**doc, "title": title, "version": doc["version"] + 1})
    response.headers["ETag"] = f'W/"{doc["version"] + 1}"'
    return response