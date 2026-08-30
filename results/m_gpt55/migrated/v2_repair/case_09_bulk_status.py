"""Bulk endpoint returning multi-status, migrated from Flask to FastAPI."""

import json
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

_KNOWN = {"a", "b", "c"}


def _request_is_json(request: Request) -> bool:
    content_type = request.headers.get("content-type", "")
    mimetype = content_type.split(";", 1)[0].strip().lower()
    return mimetype == "application/json" or mimetype.endswith("+json")


async def _flask_get_json_silent(request: Request) -> Any:
    if not _request_is_json(request):
        return None
    try:
        body = await request.body()
        return json.loads(body)
    except Exception:
        return None


@app.post("/bulk/verify")
async def bulk_verify(request: Request):
    payload = await _flask_get_json_silent(request)
    if payload is None:
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