import json

from fastapi import FastAPI, Request
from fastapi.responses import Response


app = FastAPI()

_USERS = {"u1": {"id": "u1", "name": "ana", "tier": "pro"}}
_BALANCES = {"u1": 50}
DEPRECATION = "version=1; sunset=2027-01-01"


def _v1_headers(response):
    response.headers["X-API-Deprecation"] = DEPRECATION
    return response


def _json_response(data, status_code=200):
    body = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return Response(content=body.encode("utf-8"), media_type="application/json", status_code=status_code)


async def _get_json(request):
    raw = await request.body()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


@app.get("/v1/users/{user_id}")
async def v1_get_user(user_id: str):
    user = _USERS.get(user_id, {})
    return _v1_headers(_json_response(user, 200))


@app.get("/v2/users/{user_id}")
async def v2_get_user(user_id: str):
    user = _USERS.get(user_id)
    if user is None:
        return _json_response({"message": "user not found"}, 404)
    return _json_response({"data": user})


@app.post("/v1/charge")
async def v1_charge(request: Request):
    body = await _get_json(request) or {}
    user_id = body.get("user_id")
    amount = body.get("amount")

    if not user_id:
        return _v1_headers(_json_response({"error": "user_id required", "ok": False}, 200))
    if not isinstance(amount, int):
        return _v1_headers(_json_response({"error": "amount must be an integer", "ok": False}, 200))
    balance = _BALANCES.get(user_id)
    if balance is None:
        return _v1_headers(_json_response({"error": "unknown user", "ok": False}, 200))
    if amount > balance:
        return _v1_headers(_json_response({"error": "insufficient funds", "ok": False}, 200))
    return _v1_headers(_json_response({"ok": True, "remaining": balance - amount}, 200))


@app.post("/v2/charge")
async def v2_charge(request: Request):
    body = await _get_json(request) or {}
    if "user_id" not in body:
        return _json_response({"field": "user_id", "message": "user_id required"}, 422)
    amount = body.get("amount")
    if not isinstance(amount, int):
        return _json_response({"field": "amount", "message": "amount must be an integer"}, 422)
    balance = _BALANCES.get(body["user_id"])
    if balance is None:
        return _json_response({"message": "unknown user"}, 404)
    if amount > balance:
        return _json_response({"balance": balance, "message": "insufficient funds"}, 402)
    return _json_response({"remaining": balance - amount}, 200)


@app.get("/v1/ping")
async def v1_ping():
    return _v1_headers(Response(content=b"pong", media_type="text/html", status_code=200))


@app.get("/v2/ping")
async def v2_ping():
    return _json_response("pong")


@app.post("/v2/batch")
async def v2_batch(request: Request):
    body = await _get_json(request)
    if not isinstance(body, list):
        return _json_response({"message": "body must be a JSON array"}, 422)

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
    return _json_response({"outcomes": outcomes, "failures": failures}, status)


@app.get("/v1/config")
async def v1_config():
    return _v1_headers(_json_response({
        "deprecated": True,
        "deprecation": DEPRECATION,
        "isDeprecated": True,
        "tiers": ["free", "pro"],
    }, 200))