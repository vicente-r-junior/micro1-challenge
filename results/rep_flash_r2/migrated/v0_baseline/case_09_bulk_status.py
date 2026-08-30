from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import json

app = FastAPI()

_KNOWN = {"a", "b", "c"}


class BulkResult(BaseModel):
    index: int
    status: str
    reason: Optional[str] = None


class BulkResponse(BaseModel):
    results: List[BulkResult]
    failed: int


@app.post("/bulk/verify", response_model=BulkResponse, response_model_exclude_none=True)
async def bulk_verify(request: Request, response: Response):
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"error": "body must be JSON"})
    if payload is None:
        return JSONResponse(status_code=400, content={"error": "body must be JSON"})
    if not isinstance(payload, list):
        return JSONResponse(status_code=400, content={"error": "body must be a JSON array"})
    if not payload:
        return JSONResponse(status_code=400, content={"error": "array must not be empty"})

    results = []
    for index, key in enumerate(payload):
        if not isinstance(key, str):
            results.append({"index": index, "status": "invalid", "reason": "not a string"})
        elif key in _KNOWN:
            results.append({"index": index, "status": "ok"})
        else:
            results.append({"index": index, "status": "unknown"})

    failed = sum(1 for r in results if r["status"] != "ok")
    status = 200 if failed == 0 else 207
    response.status_code = status
    return BulkResponse(results=[BulkResult(**r) for r in results], failed=failed)


@app.get("/bulk/limits")
async def limits():
    return {"max_items": 100, "known": sorted(_KNOWN)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)