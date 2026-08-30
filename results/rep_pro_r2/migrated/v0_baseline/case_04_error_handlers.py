"""Centralised error handling. Migrated from Flask to FastAPI.

Exercises: exception handlers for a custom exception and for HTTP exceptions,
manual 404/405 handling, and a uniform error envelope every client parses.
"""

from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

_ACCOUNTS = {"a1": {"id": "a1", "balance": 100}}


class InsufficientFunds(Exception):
    def __init__(self, needed, available):
        super().__init__("insufficient funds")
        self.needed = needed
        self.available = available


class WithdrawRequest(BaseModel):
    amount: int = Field(gt=0, strict=True)


@app.exception_handler(InsufficientFunds)
async def on_insufficient_funds(request: Request, exc: InsufficientFunds):
    return JSONResponse(
        status_code=409,
        content={"error": "insufficient_funds", "needed": exc.needed, "available": exc.available},
    )


@app.exception_handler(StarletteHTTPException)
async def on_http_error(request: Request, exc: StarletteHTTPException):
    message = HTTPStatus(exc.status_code).phrase
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "http_error", "status": exc.status_code, "message": message},
    )


@app.get("/accounts/{account_id}")
async def get_account(account_id: str):
    account = _ACCOUNTS.get(account_id)
    if account is None:
        return JSONResponse(
            status_code=404, content={"error": "not_found", "resource": "account"}
        )
    return account


@app.post("/accounts/{account_id}/withdraw")
async def withdraw(account_id: str, request: Request):
    account = _ACCOUNTS.get(account_id)
    if account is None:
        return JSONResponse(
            status_code=404, content={"error": "not_found", "resource": "account"}
        )

    try:
        body = await request.json() or {}
    except Exception:
        body = {}

    try:
        data = WithdrawRequest.model_validate(body)
    except ValidationError:
        return JSONResponse(status_code=400, content={"error": "bad_amount"})

    amount = data.amount
    if amount > account["balance"]:
        raise InsufficientFunds(amount, account["balance"])

    return {"id": account_id, "withdrawn": amount, "balance": account["balance"] - amount}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)