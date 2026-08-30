"""Bulk endpoint returning multi-status. FastAPI migration."""

import json
from typing import Any, Dict, List

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

_KNOWN = {"a", "b", "c"}


class LimitsResponse(BaseModel):
    known: List[str]
    max_items: int


class VerifyResponse(BaseModel):
    failed: int
    results: List[Dict[str, Any]]


@app.get("/bulk/limits")
async def limits():
    payload = LimitsResponse(known=sorted(_KNOWN), max_items=100)
    return JSONResponse(content=payload.model_dump())


@app.post("/bulk/verify")
async def bulk_verify(request: Request):
    content_type = request.headers.get("content-type", "")
    mimetype = content_type.split(";", 1)[0].strip().lower()
    if mimetype != "application/json" and not mimetype.endswith("+json"):
        return JSONResponse(content={"error": "body must be JSON"}, status_code=400)

    try:
        payload = json.loads(await request.body())
    except ValueError:
        return JSONResponse(content={"error": "body must be JSON"}, status_code=400)

    if payload is None:
        return JSONResponse(content={"error": "body must be JSON"}, status_code=400)
    if not isinstance(payload, list):
        return JSONResponse(content={"error": "body must be a JSON array"}, status_code=400)
    if not payload:
        return JSONResponse(content={"error": "array must not be empty"}, status_code=400)

    results = []
    for index, key in enumerate(payload):
        if not isinstance(key, str):
            results.append({"index": index, "reason": "not a string", "status": "invalid"})
        elif key in _KNOWN:
            results.append({"index": index, "status": "ok"})
        else:
            results.append({"index": index, "status": "unknown"})

    failed = sum(1 for r in results if r["status"] != "ok")
    status = 200 if failed == 0 else 207
    response = VerifyResponse(failed=failed, results=results)
    return JSONResponse(content=response.model_dump(), status_code=status)