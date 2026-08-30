"""A gateway that grew over six years. Synthetic case for this benchmark.

This is the shape legacy code actually has: three generations of error handling
living side by side because each was added by a different person under a
different deadline, and clients were written against whichever one existed at
the time.

Nothing here is good design. That is the point. A migration is not allowed to
tidy it up, because every inconsistency below is load-bearing for somebody.

Traps, in order of how often a rewrite normalises them away:
  * three different error envelopes: {"error": ...}, {"message": ...}, and a
    bare string body
  * /v1/charge answers 200 with an error payload -- the status is a lie, and a
    client checks the body
  * /v1/users/<id> returns 200 with an empty object for a missing user, while
    /v2/users/<id> returns a proper 404
  * a deprecation header only on the v1 routes
  * a status that depends on a computed value (207 vs 200)
  * an endpoint that returns a JSON string, not a JSON object
"""

import json
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request, Response
from pydantic import BaseModel

app = FastAPI()

_USERS = {"u1": {"id": "u1", "name": "ana", "tier": "pro"}}
_BALANCES = {"u1": 50}
DEPRECATION = "version=1; sunset=2027-01-01"


class V1ConfigModel(BaseModel):
    deprecation: str
    deprecated: bool
    isDeprecated: bool
    tiers: List[str]


def _json_response(content: Any, status_code: int = 200, headers: Optional[Dict[str, str]] = None) -> Response:
    body = json.dumps(content, sort_keys=True, separators=(",", ":"))
    return Response(
        content=body,
        media_type="application/json",
        status_code=status_code,
        headers=headers,
    )


def _v1_json_response(content: Any, status_code: int = 200) -> Response:
    return _json_response(
        content,
        status_code=status_code,
        headers={"X-API-Deprecation": DEPRECATION},
    )


def _v1_text_response(content: str, media_type: str, status_code: int = 200) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        status_code=status_code,
        headers={"X-API-Deprecation": DEPRECATION},
    )


async def _json_body(request: Request) -> Any:
    try:
        raw = await request.body()
        return json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


@app.get("/v1/users/{user_id}")
async def v1_get_user(user_id: str):
    user = _USERS.get(user_id, {})
    return _v1_json_response(user)


@app.get("/v2/users/{user_id}")
async def v2_get_user(user_id: str):
    user = _USERS.get(user_id)
    if user is None:
        return _json_response({"message": "user not found"}, status_code=404)
    return _json_response({"data": user})


@app.post("/v1/charge")
async def v1_charge(request: Request):
    body = await _json_body(request) or {}
    user_id = body.get("user_id")
    amount = body.get("amount")

    if not user_id:
        return _v1_json_response({"ok": False, "error": "user_id required"})
    if not isinstance(amount, int):
        return _v1_json_response({"ok": False, "error": "amount must be an integer"})
    balance = _BALANCES.get(user_id)
    if balance is None:
        return _v1_json_response({"ok": False, "error": "unknown user"})
    if amount > balance:
        return _v1_json_response({"ok": False, "error": "insufficient funds"})
    return _v1_json_response({"ok": True, "remaining": balance - amount})


@app.post("/v2/charge")
async def v2_charge(request: Request):
    body = await _json_body(request) or {}
    if "user_id" not in body:
        return _json_response(
            {"message": "user_id required", "field": "user_id"},
            status_code=422,
        )
    amount = body.get("amount")
    if not isinstance(amount, int):
        return _json_response(
            {"message": "amount must be an integer", "field": "amount"},
            status_code=422,
        )
    balance = _BALANCES.get(body["user_id"])
    if balance is None:
        return _json_response({"message": "unknown user"}, status_code=404)
    if amount > balance:
        return _json_response(
            {"message": "insufficient funds", "balance": balance},
            status_code=402,
        )
    return _json_response({"remaining": balance - amount})


@app.get("/v1/ping")
async def v1_ping():
    return _v1_text_response("pong", "text/html; charset=utf-8")


@app.get("/v2/ping")
async def v2_ping():
    return _json_response("pong")


@app.post("/v2/batch")
async def v2_batch(request: Request):
    body = await _json_body(request)
    if not isinstance(body, list):
        return _json_response({"message": "body must be a JSON array"}, status_code=422)

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
    return _json_response({"outcomes": outcomes, "failures": failures}, status_code=status)


@app.get("/v1/config")
async def v1_config():
    config = V1ConfigModel(
        deprecation=DEPRECATION,
        deprecated=True,
        isDeprecated=True,
        tiers=["free", "pro"],
    ).model_dump()
    return _v1_json_response(config)