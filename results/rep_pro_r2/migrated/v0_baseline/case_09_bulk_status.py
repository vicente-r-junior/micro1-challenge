from typing import List, Literal, Optional

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

_KNOWN = {"a", "b", "c"}


class VerifyItemResult(BaseModel):
    index: int
    status: Literal["ok", "invalid", "unknown"]
    reason: Optional[str] = None


class VerifyResponse(BaseModel):
    results: List[VerifyItemResult]
    failed: int


class LimitsResponse(BaseModel):
    max_items: int
    known: List[str]


app = FastAPI()


@app.post(
    "/bulk/verify",
    response_model=VerifyResponse,
    response_model_exclude_none=True,
)
async def bulk_verify(request: Request, response: Response):
    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "body must be JSON"})

    if payload is None:
        return JSONResponse(status_code=400, content={"error": "body must be JSON"})

    if not isinstance(payload, list):
        return JSONResponse(status_code=400, content={"error": "body must be a JSON array"})

    if not payload:
        return JSONResponse(status_code=400, content={"error": "array must not be empty"})

    results: List[VerifyItemResult] = []
    for index, key in enumerate(payload):
        if not isinstance(key, str):
            results.append(VerifyItemResult(index=index, status="invalid", reason="not a string"))
        elif key in _KNOWN:
            results.append(VerifyItemResult(index=index, status="ok"))
        else:
            results.append(VerifyItemResult(index=index, status="unknown"))

    failed = sum(1 for result in results if result.status != "ok")
    response.status_code = 200 if failed == 0 else 207
    return VerifyResponse(results=results, failed=failed)


@app.get("/bulk/limits", response_model=LimitsResponse)
async def limits():
    return LimitsResponse(max_items=100, known=sorted(_KNOWN))