from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

_ACCOUNTS = {"a1": {"id": "a1", "balance": 100}}


class InsufficientFunds(Exception):
    def __init__(self, needed, available):
        super().__init__("insufficient funds")
        self.needed = needed
        self.available = available


class WithdrawRequest(BaseModel):
    amount: int = Field(gt=0)


@app.exception_handler(InsufficientFunds)
async def on_insufficient_funds(request: Request, exc: InsufficientFunds):
    return JSONResponse(
        status_code=409,
        content={
            "error": "insufficient_funds",
            "needed": exc.needed,
            "available": exc.available,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def on_http_error(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "status": exc.status_code,
            "message": HTTPStatus(exc.status_code).phrase,
        },
    )


@app.exception_handler(RequestValidationError)
async def on_request_validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "bad_amount"})


@app.get("/accounts/{account_id}")
async def get_account(account_id: str):
    account = _ACCOUNTS.get(account_id)
    if account is None:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "resource": "account"},
        )
    return account


@app.post("/accounts/{account_id}/withdraw")
async def withdraw(account_id: str, payload: WithdrawRequest):
    account = _ACCOUNTS.get(account_id)
    if account is None:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "resource": "account"},
        )

    amount = payload.amount
    if amount > account["balance"]:
        raise InsufficientFunds(amount, account["balance"])

    return {
        "id": account_id,
        "withdrawn": amount,
        "balance": account["balance"] - amount,
    }