from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

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
            "message": exc.detail,
        },
    )


@app.get("/accounts/{account_id}")
async def get_account(account_id: str):
    account = _ACCOUNTS.get(account_id)
    if account is None:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "resource": "account"},
        )
    return JSONResponse(content=account)


@app.post("/accounts/{account_id}/withdraw")
async def withdraw(account_id: str, request: Request):
    account = _ACCOUNTS.get(account_id)
    if account is None:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "resource": "account"},
        )

    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type == "application/json" or content_type.endswith("+json"):
        try:
            data = await request.json()
        except Exception:
            data = {}
    else:
        data = {}
    if not data:
        data = {}

    amount = data.get("amount")
    if not isinstance(amount, int) or amount <= 0:
        return JSONResponse(
            status_code=400,
            content={"error": "bad_amount"},
        )
    if amount > account["balance"]:
        raise InsufficientFunds(amount, account["balance"])
    return JSONResponse(
        content={
            "id": account_id,
            "withdrawn": amount,
            "balance": account["balance"] - amount,
        }
    )