from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

_ACCOUNTS = {"a1": {"id": "a1", "balance": 100}}

class InsufficientFunds(Exception):
    def __init__(self, needed, available):
        super().__init__("insufficient funds")
        self.needed = needed
        self.available = available

class ErrorResponse(BaseModel):
    error: str
    needed: Optional[int] = None
    available: Optional[int] = None
    resource: Optional[str] = None
    status: Optional[int] = None
    message: Optional[str] = None

@app.exception_handler(InsufficientFunds)
async def on_insufficient_funds(request, exc):
    return JSONResponse(content={"error": "insufficient_funds", "needed": exc.needed, "available": exc.available}, status_code=409)

@app.exception_handler(HTTPException)
async def on_http_error(request, exc):
    return JSONResponse(content={"error": "http_error", "status": exc.status_code, "message": exc.detail}, status_code=exc.status_code)

@app.get("/accounts/{account_id}")
async def get_account(account_id: str):
    account = _ACCOUNTS.get(account_id)
    if account is None:
        return JSONResponse(content={"error": "not_found", "resource": "account"}, status_code=404)
    return account

class WithdrawRequest(BaseModel):
    amount: Optional[int] = None

@app.post("/accounts/{account_id}/withdraw")
async def withdraw(account_id: str, request: WithdrawRequest):
    account = _ACCOUNTS.get(account_id)
    if account is None:
        return JSONResponse(content={"error": "not_found", "resource": "account"}, status_code=404)
    amount = request.amount
    if amount is None or not isinstance(amount, int) or amount <= 0:
        return JSONResponse(content={"error": "bad_amount"}, status_code=400)
    if amount > account["balance"]:
        raise InsufficientFunds(amount, account["balance"])
    account["balance"] -= amount
    return {"id": account_id, "withdrawn": amount, "balance": account["balance"]}