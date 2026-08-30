import json
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class SortedJSONResponse(JSONResponse):
    def render(self, content):
        return (json.dumps(
            content,
            ensure_ascii=True,
            allow_nan=True,
            indent=None,
            separators=(",", ":"),
            sort_keys=True,
        ) + "\n").encode("utf-8")


app = FastAPI(
    default_response_class=SortedJSONResponse,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

_ACCOUNTS = {"a1": {"id": "a1", "balance": 100}}


class InsufficientFunds(Exception):
    def __init__(self, needed, available):
        super().__init__("insufficient funds")
        self.needed = needed
        self.available = available


def _is_json_request(request: Request) -> bool:
    content_type = request.headers.get("content-type", "")
    media_type = content_type.split(";", 1)[0].strip().lower()
    if media_type == "application/json":
        return True
    return media_type.startswith("application/") and media_type.endswith("+json")


async def _read_json_or_empty(request: Request):
    if not _is_json_request(request):
        return {}
    body = await request.body()
    if not body:
        return {}
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return data or {}


@app.exception_handler(InsufficientFunds)
async def on_insufficient_funds(request: Request, exc: InsufficientFunds):
    return SortedJSONResponse(
        {
            "error": "insufficient_funds",
            "needed": exc.needed,
            "available": exc.available,
        },
        status_code=409,
    )


@app.exception_handler(StarletteHTTPException)
async def on_http_error(request: Request, exc: StarletteHTTPException):
    try:
        message = HTTPStatus(exc.status_code).phrase
    except ValueError:
        message = exc.detail
    return SortedJSONResponse(
        {
            "error": "http_error",
            "status": exc.status_code,
            "message": message,
        },
        status_code=exc.status_code,
    )


@app.get("/accounts/{account_id}")
async def get_account(account_id: str):
    account = _ACCOUNTS.get(account_id)
    if account is None:
        return SortedJSONResponse(
            {"error": "not_found", "resource": "account"},
            status_code=404,
        )
    return account


@app.post("/accounts/{account_id}/withdraw")
async def withdraw(account_id: str, request: Request):
    account = _ACCOUNTS.get(account_id)
    if account is None:
        return SortedJSONResponse(
            {"error": "not_found", "resource": "account"},
            status_code=404,
        )
    data = await _read_json_or_empty(request)
    amount = data.get("amount")
    if not isinstance(amount, int) or amount <= 0:
        return SortedJSONResponse({"error": "bad_amount"}, status_code=400)
    if amount > account["balance"]:
        raise InsufficientFunds(amount, account["balance"])
    return {
        "id": account_id,
        "withdrawn": amount,
        "balance": account["balance"] - amount,
    }