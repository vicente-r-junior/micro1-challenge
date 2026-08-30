import json
from typing import Any
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

_USERS = {"u1": {"id": "u1", "name": "ana", "tier": "pro"}}
_BALANCES = {"u1": 50}
DEPRECATION = "version=1; sunset=2027-01-01"


class User(BaseModel):
    id: str
    name: str
    tier: str


def _v1_headers(response: Response) -> Response:
    response.headers["X-API-Deprecation"] = DEPRECATION
    return response


def _v1_json_response(content, status_code: int = 200):
    response = JSONResponse(content=content, status_code=status_code)
    return _v1_headers(response)


async def _parse_json_body(request: Request) -> Any:
    content_type = request.headers.get("content-type", "")
    mimetype = content_type.split(";")[0].strip().lower()
    if not (mimetype == "application/json" or (mimetype.startswith("application/") and mimetype.endswith("+json"))):
        return None
    raw = await request.body()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


@app.get("/v1/users/{user_id}")
async def v1_get_user(user_id: str):
    user = _USERS.get(user_id, {})
    return _v1_json_response(user, 200)


@app.get("/v2/users/{user_id}")
async def v2_get_user(user_id: str):
    user = _USERS.get(user_id)
    if user is None:
        return JSONResponse(content={"message": "user not found"}, status_code=404)
    user_model = User(**user)
    return JSONResponse(content={"data": user_model.model_dump()}, status_code=200)


@app.post("/v1/charge")
async def v1_charge(request: Request):
    body = (await _parse_json_body(request)) or {}
    user_id = body.get("user_id")
    amount = body.get("amount")

    if not user_id:
        return _v1_json_response({"ok": False, "error": "user_id required"}, 200)
    if not isinstance(amount, int):
        return _v1_json_response({"ok": False, "error": "amount must be an integer"}, 200)
    balance = _BALANCES.get(user_id)
    if balance is None:
        return _v1_json_response({"ok": False, "error": "unknown user"}, 200)
    if amount > balance:
        return _v1_json_response({"ok": False, "error": "insufficient funds"}, 200)
    return _v1_json_response({"ok": True, "remaining": balance - amount}, 200)


@app.post("/v2/charge")
async def v2_charge(request: Request):
    body = (await _parse_json_body(request)) or {}
    if "user_id" not in body:
        return JSONResponse(content={"message": "user_id required", "field": "user_id"}, status_code=422)
    amount = body.get("amount")
    if not isinstance(amount, int):
        return JSONResponse(content={"message": "amount must be an integer", "field": "amount"}, status_code=422)
    balance = _BALANCES.get(body["user_id"])
    if balance is None:
        return JSONResponse(content={"message": "unknown user"}, status_code=404)
    if amount > balance:
        return JSONResponse(content={"message": "insufficient funds", "balance": balance}, status_code=402)
    return JSONResponse(content={"remaining": balance - amount}, status_code=200)


@app.get("/v1/ping")
async def v1_ping():
    response = Response(content="pong", media_type="text/html")
    return _v1_headers(response)


@app.get("/v2/ping")
async def v2_ping():
    return JSONResponse(content="pong")


@app.post("/v2/batch")
async def v2_batch(request: Request):
    body = await _parse_json_body(request)
    if not isinstance(body, list):
        return JSONResponse(content={"message": "body must be a JSON array"}, status_code=422)

    outcomes = []
    for index, entry in enumerate(body):
        if not isinstance(entry, dict) or "user_id" not in entry:
            outcomes.append({"index": index, "ok": False, "error": "malformed entry"})
        elif entry["user_id"] not in _USERS:
            outcomes.append({"index": index, "ok": False, "error": "unknown user"})
        else:
            outcomes.append({"index": index, "ok": True})

    failures = sum(1 for o in outcomes if not o["ok"])
    status = 200 if failures == 0 else 207
    return JSONResponse(content={"outcomes": outcomes, "failures": failures}, status_code=status)


@app.get("/v1/config")
async def v1_config():
    return _v1_json_response({
        "deprecation": DEPRECATION,
        "deprecated": True,
        "isDeprecated": True,
        "tiers": ["free", "pro"],
    })