from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

_KNOWN = {"a", "b", "c"}

class BulkResult(BaseModel):
    index: int
    status: str
    reason: Optional[str] = None

class VerifyResponse(BaseModel):
    results: list[BulkResult]
    failed: int

@app.post("/bulk/verify")
async def bulk_verify(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "body must be JSON"})
    if not isinstance(payload, list):
        return JSONResponse(status_code=400, content={"error": "body must be a JSON array"})
    if not payload:
        return JSONResponse(status_code=400, content={"error": "array must not be empty"})

    results: list[BulkResult] = []
    for index, key in enumerate(payload):
        if not isinstance(key, str):
            results.append(BulkResult(index=index, status="invalid", reason="not a string"))
        elif key in _KNOWN:
            results.append(BulkResult(index=index, status="ok"))
        else:
            results.append(BulkResult(index=index, status="unknown"))

    failed = sum(1 for r in results if r.status != "ok")
    status_code = 200 if failed == 0 else 207
    data = VerifyResponse(results=results, failed=failed)
    return JSONResponse(status_code=status_code, content=data.model_dump(exclude_none=True))


@app.get("/bulk/limits")
async def limits():
    return JSONResponse(content={"max_items": 100, "known": sorted(_KNOWN)})