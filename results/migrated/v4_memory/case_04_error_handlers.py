from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import http
import json

app = FastAPI()

_ACCOUNTS = {"a1": {"id": "a1", "balance": 100}}


class InsufficientFunds(Exception):
    def __init__(self, needed: int, available: int):
        super().__init__("insufficient funds")
        self.needed = needed
        self.available = available


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
    status_code = exc.status_code
    message = http.HTTPStatus(status_code).phrase
    return JSONResponse(
        status_code=status_code,
        content={"error": "http_error", "status": status_code, "message": message},
    )


async def _get_json_silent(request: Request):
    content_type = request.headers.get("content-type", "")
    mimetype = content_type.split(";", 1)[0].strip().lower()
    is_json = mimetype == "application/json" or (
        mimetype.startswith("application/") and mimetype.endswith("+json")
    )
    if not is_json:
        return None
    body = await request.body()
    if not body:
        return None
    try:
        return json.loads(body)
    except (ValueError, TypeError):
        return None


@app.get("/accounts/{account_id}")
async def get_account(account_id: str):
    account = _ACCOUNTS.get(account_id)
    if account is None:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "resource": "account"},
        )
    return JSONResponse(status_code=200, content=account)


@app.post("/accounts/{account_id}/withdraw")
async def withdraw(account_id: str, request: Request):
    account = _ACCOUNTS.get(account_id)
    if account is None:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "resource": "account"},
        )
    data = await _get_json_silent(request) or {}
    amount = data.get("amount")
    if not isinstance(amount, int) or amount <= 0:
        return JSONResponse(
            status_code=400,
            content={"error": "bad_amount"},
        )
    if amount > account["balance"]:
        raise InsufficientFunds(amount, account["balance"])
    return JSONResponse(
        status_code=200,
        content={
            "id": account_id,
            "withdrawn": amount,
            "balance": account["balance"] - amount,
        },
    )