"""Centralised error handling migrated from Flask to FastAPI.

Exercises: custom exception handling, centralized HTTP 404/405 handling,
manual JSON parsing to preserve Flask's request.get_json(silent=True) behavior,
and a uniform error envelope every client parses.
"""

from __future__ import annotations

from json import JSONDecodeError
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

_ACCOUNTS: dict[str, dict[str, Any]] = {"a1": {"id": "a1", "balance": 100}}


class Account(BaseModel):
    id: str
    balance: int


class WithdrawRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    amount: Any = None


class WithdrawResponse(BaseModel):
    id: str
    withdrawn: int
    balance: int


class InsufficientFunds(Exception):
    def __init__(self, needed: int, available: int):
        super().__init__("insufficient funds")
        self.needed = needed
        self.available = available


@app.exception_handler(InsufficientFunds)
async def on_insufficient_funds(request: Request, exc: InsufficientFunds) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "error": "insufficient_funds",
            "needed": exc.needed,
            "available": exc.available,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def on_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "status": exc.status_code,
            "message": detail,
        },
    )


@app.get("/accounts/{account_id}", response_model=Account)
async def get_account(account_id: str) -> Account | JSONResponse:
    account = _ACCOUNTS.get(account_id)
    if account is None:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "resource": "account"},
        )
    return Account.model_validate(account)


@app.post("/accounts/{account_id}/withdraw", response_model=WithdrawResponse)
async def withdraw(account_id: str, request: Request) -> WithdrawResponse | JSONResponse:
    account = _ACCOUNTS.get(account_id)
    if account is None:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "resource": "account"},
        )

    try:
        raw_data = await request.json()
    except (JSONDecodeError, ValueError):
        raw_data = {}

    if not isinstance(raw_data, dict):
        raw_data = {}

    data = WithdrawRequest.model_validate(raw_data)
    amount = data.amount

    if not isinstance(amount, int) or amount <= 0:
        return JSONResponse(status_code=400, content={"error": "bad_amount"})

    balance = int(account["balance"])
    if amount > balance:
        raise InsufficientFunds(amount, balance)

    return WithdrawResponse(
        id=account_id,
        withdrawn=amount,
        balance=balance - amount,
    )