"""Bulk endpoint returning multi-status. Synthetic case for this benchmark.

Exercises: a JSON *array* request body (not an object), per-item outcomes, HTTP
207, and a partial-failure path that still returns 2xx.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

_KNOWN = {"a", "b", "c"}


class ErrorResponse(BaseModel):
    error: str


class BulkVerifyResult(BaseModel):
    index: int
    status: Literal["invalid", "ok", "unknown"]
    reason: str | None = None


class BulkVerifyResponse(BaseModel):
    results: list[BulkVerifyResult]
    failed: int


class LimitsResponse(BaseModel):
    max_items: int
    known: list[str]


def _is_json_content_type(request: Request) -> bool:
    content_type = request.headers.get("content-type")
    if not content_type:
        return False

    mimetype = content_type.split(";", 1)[0].strip().lower()
    return mimetype == "application/json" or (
        mimetype.startswith("application/") and mimetype.endswith("+json")
    )


async def _get_json_flask_silent(request: Request) -> Any | None:
    """Approximate Flask's request.get_json(silent=True) behavior."""
    if not _is_json_content_type(request):
        return None

    body = await request.body()
    if not body:
        return None

    try:
        return json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _json_response(model: BaseModel, status_code: int = status.HTTP_200_OK) -> JSONResponse:
    return JSONResponse(
        content=model.model_dump(mode="json", exclude_none=True),
        status_code=status_code,
    )


@app.post("/bulk/verify")
async def bulk_verify(request: Request) -> JSONResponse:
    payload = await _get_json_flask_silent(request)
    if payload is None:
        return _json_response(
            ErrorResponse(error="body must be JSON"),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if not isinstance(payload, list):
        return _json_response(
            ErrorResponse(error="body must be a JSON array"),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if not payload:
        return _json_response(
            ErrorResponse(error="array must not be empty"),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    results: list[BulkVerifyResult] = []
    for index, key in enumerate(payload):
        if not isinstance(key, str):
            results.append(
                BulkVerifyResult(index=index, status="invalid", reason="not a string")
            )
        elif key in _KNOWN:
            results.append(BulkVerifyResult(index=index, status="ok"))
        else:
            results.append(BulkVerifyResult(index=index, status="unknown"))

    failed = sum(1 for result in results if result.status != "ok")
    response_status = status.HTTP_200_OK if failed == 0 else status.HTTP_207_MULTI_STATUS
    return _json_response(
        BulkVerifyResponse(results=results, failed=failed),
        status_code=response_status,
    )


@app.get("/bulk/limits", response_model=LimitsResponse)
def limits() -> LimitsResponse:
    return LimitsResponse(max_items=100, known=sorted(_KNOWN))