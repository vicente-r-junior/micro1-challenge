from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import HTTP_404_NOT_FOUND, HTTP_405_METHOD_NOT_ALLOWED

app = FastAPI()

_ACCOUNTS = {"a1": {"id": "a1", "balance": 100}}


class InsufficientFunds(Exception):
    def __init__(self, needed, available):
        super().__init__("insufficient funds")
        self.needed = needed
        self.available = available


@app.exception_handler(InsufficientFunds)
async def on_insufficient_funds(request: Request, exc: InsufficientFunds):
    return JSONResponse(
        content={"error": "insufficient_funds", "needed": exc.needed, "available": exc.available},
        status_code=409,
    )


@app.exception_handler(StarletteHTTPException)
async def on_http_error(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        content={"error": "http_error", "status": exc.status_code, "message": exc.detail if isinstance(exc.detail, str) else exc.__class__.__name__},
        status_code=exc.status_code,
    )


@app.get("/accounts/{account_id}")
async def get_account(account_id: str):
    account = _ACCOUNTS.get(account_id)
    if account is None:
        return JSONResponse(content={"error": "not_found", "resource": "account"}, status_code=404)
    return account


@app.post("/accounts/{account_id}/withdraw")
async def withdraw(account_id: str, request: Request):
    account = _ACCOUNTS.get(account_id)
    if account is None:
        return JSONResponse(content={"error": "not_found", "resource": "account"}, status_code=404)
    data = await request.json()
    if not isinstance(data, dict):
        data = {}
    amount = data.get("amount")
    if not isinstance(amount, int) or amount <= 0:
        return JSONResponse(content={"error": "bad_amount"}, status_code=400)
    if amount > account["balance"]:
        raise InsufficientFunds(amount, account["balance"])
    return {"id": account_id, "withdrawn": amount, "balance": account["balance"] - amount}