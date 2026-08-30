from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Literal, Union

app = FastAPI()

_KNOWN = {"a", "b", "c"}


class ResultOk(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index: int
    status: Literal["ok"]


class ResultUnknown(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index: int
    status: Literal["unknown"]


class ResultInvalid(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index: int
    status: Literal["invalid"]
    reason: str


Result = Union[ResultOk, ResultUnknown, ResultInvalid]


class BulkVerifyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    results: List[Result]
    failed: int


class LimitsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_items: int = Field(default=100)
    known: List[str]


@app.post("/bulk/verify")
async def bulk_verify(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "body must be JSON"}, status_code=400)

    if not isinstance(payload, list):
        return JSONResponse({"error": "body must be a JSON array"}, status_code=400)
    if not payload:
        return JSONResponse({"error": "array must not be empty"}, status_code=400)

    results = []
    for index, key in enumerate(payload):
        if not isinstance(key, str):
            results.append({"index": index, "status": "invalid", "reason": "not a string"})
        elif key in _KNOWN:
            results.append({"index": index, "status": "ok"})
        else:
            results.append({"index": index, "status": "unknown"})

    failed = sum(1 for r in results if r["status"] != "ok")
    status_code = 200 if failed == 0 else 207
    return JSONResponse({"results": results, "failed": failed}, status_code=status_code)


@app.get("/bulk/limits")
async def limits():
    return JSONResponse({"max_items": 100, "known": sorted(_KNOWN)})