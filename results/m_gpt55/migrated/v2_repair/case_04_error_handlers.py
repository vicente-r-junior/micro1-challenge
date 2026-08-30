from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(redirect_slashes=False)

_ACCOUNTS = {"a1": {"id": "a1", "balance": 100}}


class InsufficientFunds(Exception):
    def __init__(self, needed: int, available: int):
        super().__init__("insufficient funds")
        self.needed = needed
        self.available = available


def _http_message(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "Unknown Error"


def _is_json_mimetype(content_type: str | None) -> bool:
    if not content_type:
        return False
    mimetype = content_type.split(";", 1)[0].strip().lower()
    return mimetype == "application/json" or (
        mimetype.startswith("application/") and mimetype.endswith("+json")
    )


async def _get_json_silent(request: Request) -> Any:
    if not _is_json_mimetype(request.headers.get("content-type")):
        return None
    try:
        body = await request.body()
        return json.loads(body)
    except Exception:
        return None


@app.exception_handler(InsufficientFunds)
async def on_insufficient_funds(request: Request, exc: InsufficientFunds):
    return JSONResponse(
        content={
            "error": "insufficient_funds",
            "needed": exc.needed,
            "available": exc.available,
        },
        status_code=409,
    )


@app.exception_handler(StarletteHTTPException)
async def on_http_error(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        content={
            "error": "http_error",
            "status": exc.status_code,
            "message": _http_message(exc.status_code),
        },
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def on_unhandled_error(request: Request, exc: Exception):
    return JSONResponse(
        content={
            "error": "http_error",
            "status": 500,
            "message": "Internal Server Error",
        },
        status_code=500,
    )


@app.get("/accounts/{account_id}")
async def get_account(account_id: str):
    account = _ACCOUNTS.get(account_id)
    if account is None:
        return JSONResponse(
            content={"error": "not_found", "resource": "account"},
            status_code=404,
        )
    return JSONResponse(content=account)


@app.post("/accounts/{account_id}/withdraw")
async def withdraw(account_id: str, request: Request):
    account = _ACCOUNTS.get(account_id)
    if account is None:
        return JSONResponse(
            content={"error": "not_found", "resource": "account"},
            status_code=404,
        )

    data = await _get_json_silent(request) or {}
    try:
        amount = data.get("amount")
    except AttributeError:
        return JSONResponse(
            content={
                "error": "http_error",
                "status": 500,
                "message": "Internal Server Error",
            },
            status_code=500,
        )

    if not isinstance(amount, int) or amount <= 0:
        return JSONResponse(content={"error": "bad_amount"}, status_code=400)

    if amount > account["balance"]:
        raise InsufficientFunds(amount, account["balance"])

    return JSONResponse(
        content={
            "id": account_id,
            "withdrawn": amount,
            "balance": account["balance"] - amount,
        }
    )