from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

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
        status_code=409,
        content={"error": "insufficient_funds", "needed": exc.needed, "available": exc.available},
    )

@app.exception_handler(HTTPException)
async def on_http_error(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "http_error", "status": exc.status_code, "message": exc.detail},
    )

class WithdrawRequest(BaseModel):
    amount: int

@app.get("/accounts/{account_id}")
async def get_account(account_id: str):
    account = _ACCOUNTS.get(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail={"error": "not_found", "resource": "account"})
    return account

@app.post("/accounts/{account_id}/withdraw")
async def withdraw(account_id: str, request: WithdrawRequest):
    account = _ACCOUNTS.get(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail={"error": "not_found", "resource": "account"})
    amount = request.amount
    if not isinstance(amount, int) or amount <= 0:
        raise HTTPException(status_code=400, detail={"error": "bad_amount"})
    if amount > account["balance"]:
        raise InsufficientFunds(amount, account["balance"])
    account["balance"] -= amount
    return {"id": account_id, "withdrawn": amount, "balance": account["balance"]}