from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, conlist
from typing import List, Dict, Any

app = FastAPI()

_KNOWN = {"a", "b", "c"}

class BulkVerifyRequest(BaseModel):
    __root__: conlist(str)

class ResultItem(BaseModel):
    index: int
    status: str
    reason: str = None

class BulkVerifyResponse(BaseModel):
    results: List[ResultItem]
    failed: int

@app.post("/bulk/verify", response_model=BulkVerifyResponse, status_code=200)
async def bulk_verify(payload: BulkVerifyRequest):
    results = []
    for index, key in enumerate(payload.__root__):
        if not isinstance(key, str):
            results.append(ResultItem(index=index, status="invalid", reason="not a string"))
        elif key in _KNOWN:
            results.append(ResultItem(index=index, status="ok"))
        else:
            results.append(ResultItem(index=index, status="unknown"))

    failed = sum(1 for r in results if r.status != "ok")
    status = 200 if failed == 0 else 207
    return JSONResponse(content={"results": results, "failed": failed}, status_code=status)

@app.get("/bulk/limits")
async def limits():
    return JSONResponse(content={"max_items": 100, "known": sorted(_KNOWN)})