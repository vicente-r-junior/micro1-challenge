from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

_DOCS = {"d1": {"id": "d1", "title": "spec", "version": 3}}


@app.get("/docs/{doc_id}")
async def get_doc(doc_id: str):
    doc = _DOCS.get(doc_id)
    if doc is None:
        return JSONResponse(content={"error": "doc not found"}, status_code=404)
    return JSONResponse(content=doc, status_code=200, headers={"ETag": f'W/"{doc["version"]}"'})


@app.patch("/docs/{doc_id}")
async def patch_doc(doc_id: str, request: Request):
    doc = _DOCS.get(doc_id)
    if doc is None:
        return JSONResponse(content={"error": "doc not found"}, status_code=404)

    if_match = request.headers.get("If-Match")
    if not if_match:
        return JSONResponse(
            content={"error": "If-Match header is required", "code": "PRECONDITION_REQUIRED"},
            status_code=428,
        )
    if if_match != f'W/"{doc["version"]}"':
        return JSONResponse(content={"error": "version conflict", "expected": doc["version"]}, status_code=409)

    data = await request.json()
    if not isinstance(data, dict):
        data = {}
    title = data.get("title")
    if not isinstance(title, str) or not title:
        return JSONResponse(content={"error": "title must be a non-empty string"}, status_code=400)

    updated = {**doc, "title": title, "version": doc["version"] + 1}
    return JSONResponse(content=updated, status_code=200, headers={"ETag": f'W/"{doc["version"] + 1}"'})