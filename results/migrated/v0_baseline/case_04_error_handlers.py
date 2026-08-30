import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel

app = FastAPI()

_ACCOUNTS = {"a1": {"id": "a1", "balance": 100}}


class Account(BaseModel):
    id: str
    balance: int


class InsufficientFunds(Exception):
    def __init__(self, needed, available):
        super().__init__("insufficient funds")
        self.needed = needed
        self.available = available


@app.exception_handler(InsufficientFunds)
async def on_insufficient_funds(request: Request, exc: InsufficientFunds):
    return JSONResponse(
        status_code=409,
        content={"error": "insufficient_funds", "needed": exc.needed, "available": exc.available},
    )


@app.exception_handler(StarletteHTTPException)
async def on_http_error(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "http_error", "status": exc.status_code, "message": exc.detail},
    )


@app.get("/accounts/{account_id}", response_model=Account)
async def get_account(account_id: str):
    account = _ACCOUNTS.get(account_id)
    if account is None:
        return JSONResponse(status_code=404, content={"error": "not_found", "resource": "account"})
    return account


@app.post("/accounts/{account_id}/withdraw")
async def withdraw(account_id: str, request: Request):
    account = _ACCOUNTS.get(account_id)
    if account is None:
        return JSONResponse(status_code=404, content={"error": "not_found", "resource": "account"})

    data = {}
    content_type = request.headers.get("content-type", "").lower()
    if content_type.startswith("application/json"):
        body = await request.body()
        if body:
            try:
                data = json.loads(body) or {}
            except json.JSONDecodeError:
                data = {}

    amount = data.get("amount")
    if not isinstance(amount, int) or amount <= 0:
        return JSONResponse(status_code=400, content={"error": "bad_amount"})

    if amount > account["balance"]:
        raise InsufficientFunds(amount, account["balance"])

    return {"id": account_id, "withdrawn": amount, "balance": account["balance"] - amount}