from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from typing import Any

app = FastAPI()

_USERS = {"u1": {"id": "u1", "name": "ana", "tier": "pro"}}
_BALANCES = {"u1": 50}
DEPRECATION = "version=1; sunset=2027-01-01"


def _v1_headers(response: Response) -> Response:
    response.headers["X-API-Deprecation"] = DEPRECATION
    return response


@app.get("/v1/users/{user_id}")
def v1_get_user(user_id: str):
    user = _USERS.get(user_id, {})
    response = JSONResponse(content=user, status_code=200)
    return _v1_headers(response)


@app.get("/v2/users/{user_id}")
def v2_get_user(user_id: str):
    user = _USERS.get(user_id)
    if user is None:
        return JSONResponse(content={"message": "user not found"}, status_code=404)
    return JSONResponse(content={"data": user}, status_code=200)


@app.post("/v1/charge")
async def v1_charge(request: Request):
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    user_id = body.get("user_id")
    amount = body.get("amount")

    if not user_id:
        return _v1_headers(JSONResponse(content={"ok": False, "error": "user_id required"}, status_code=200))
    if not isinstance(amount, int):
        return _v1_headers(JSONResponse(content={"ok": False, "error": "amount must be an integer"}, status_code=200))
    balance = _BALANCES.get(user_id)
    if balance is None:
        return _v1_headers(JSONResponse(content={"ok": False, "error": "unknown user"}, status_code=200))
    if amount > balance:
        return _v1_headers(JSONResponse(content={"ok": False, "error": "insufficient funds"}, status_code=200))
    return _v1_headers(JSONResponse(content={"ok": True, "remaining": balance - amount}, status_code=200))


@app.post("/v2/charge")
async def v2_charge(request: Request):
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
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
def v1_ping():
    response = Response(content="pong", media_type="text/plain", status_code=200)
    return _v1_headers(response)


@app.get("/v2/ping")
def v2_ping():
    return JSONResponse(content="pong", status_code=200)


@app.post("/v2/batch")
async def v2_batch(request: Request):
    body = await request.json()
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
def v1_config():
    response = JSONResponse(
        content={
            "deprecation": DEPRECATION,
            "deprecated": True,
            "isDeprecated": True,
            "tiers": ["free", "pro"],
        },
        status_code=200,
    )
    return _v1_headers(response)