"""Bulk endpoint returning multi-status. Synthetic case for this benchmark.

Exercises: a JSON *array* request body (not an object), per-item outcomes, HTTP
207, and a partial-failure path that still returns 2xx.
"""

from typing import List, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

_KNOWN = {'a', 'b', 'c'}


class BulkResult(BaseModel):
    index: int
    status: str
    reason: Optional[str] = None


class BulkResponse(BaseModel):
    results: List[BulkResult]
    failed: int


class LimitsResponse(BaseModel):
    max_items: int
    known: List[str]


@app.post('/bulk/verify')
async def bulk_verify(request: Request):
    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse({'error': 'body must be JSON'}, status_code=400)

    if payload is None:
        return JSONResponse({'error': 'body must be JSON'}, status_code=400)
    if not isinstance(payload, list):
        return JSONResponse({'error': 'body must be a JSON array'}, status_code=400)
    if not payload:
        return JSONResponse({'error': 'array must not be empty'}, status_code=400)

    results: List[BulkResult] = []
    for index, key in enumerate(payload):
        if not isinstance(key, str):
            results.append(BulkResult(index=index, status='invalid', reason='not a string'))
        elif key in _KNOWN:
            results.append(BulkResult(index=index, status='ok'))
        else:
            results.append(BulkResult(index=index, status='unknown'))

    failed = sum(1 for r in results if r.status != 'ok')
    status_code = 200 if failed == 0 else 207
    response = BulkResponse(results=results, failed=failed)
    return JSONResponse(response.model_dump(exclude_none=True), status_code=status_code)


@app.get('/bulk/limits')
def limits():
    return LimitsResponse(max_items=100, known=sorted(_KNOWN))