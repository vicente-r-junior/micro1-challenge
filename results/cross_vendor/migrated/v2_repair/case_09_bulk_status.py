"""Bulk endpoint returning multi-status. Synthetic case for this benchmark.

Exercises: a JSON *array* request body (not an object), per-item outcomes, HTTP
207, and a partial-failure path that still returns 2xx.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, conlist
from typing import List, Dict, Any

app = FastAPI()

_KNOWN = {"a", "b", "c"}

class BulkVerifyRequest(BaseModel):
    payload: conlist(str)

@app.post("/bulk/verify")
async def bulk_verify(request: Request):
    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse(content={"error": "body must be JSON"}, status_code=400)

    if not isinstance(payload, list):
        return JSONResponse(content={"error": "body must be a JSON array"}, status_code=400)
    if not payload:
        return JSONResponse(content={"error": "array must not be empty"}, status_code=400)

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
    return JSONResponse(content={"results": results, "failed": failed}, status_code=status)

@app.get("/bulk/limits")
async def limits():
    return JSONResponse(content={"max_items": 100, "known": sorted(_KNOWN)})