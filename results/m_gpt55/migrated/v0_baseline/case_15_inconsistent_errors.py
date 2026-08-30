from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any

from fastapi import FastAPI, Request, Response
from pydantic import RootModel

app = FastAPI(redirect_slashes=False)

_USERS = {"u1": {"id": "u1", "name": "ana", "tier": "pro"}}
_BALANCES = {"u1": 50}
DEPRECATION = "version=1; sunset=2027-01-01"


class RawJson(RootModel[Any]):
    pass


def _is_json_request(request: Request) -> bool:
    content_type = request.headers.get("content-type", "")
    media_type = content_type.split(";", 1)[0].strip().lower()
    return media_type == "application/json" or (
        media_type.startswith("application/") and media_type.endswith("+json")
    )


async def _get_json_silent(request: Request) -> Any:
    if not _is_json_request(request):
        return None
    try:
        parsed = await request.json()
    except (JSONDecodeError, UnicodeDecodeError, ValueError):
        return None
    return RawJson.model_validate(parsed).root


def _json_response(content: Any, status_code: int = 200) -> Response:
    body = json.dumps(
        content,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    return Response(content=body, status_code=status_code, media_type="application/json")


def _v1_headers(response: Response) -> Response:
    response.headers["X-API-Deprecation"] = DEPRECATION
    return response


@app.get("/v1/users/{user_id}")
def v1_get_user(user_id: str) -> Response:
    user = _USERS.get(user_id, {})
    return _v1_headers(_json_response(user, 200))


@app.get("/v2/users/{user_id}")
def v2_get_user(user_id: str) -> Response:
    user = _USERS.get(user_id)
    if user is None:
        return _json_response({"message": "user not found"}, 404)
    return _json_response({"data": user}, 200)


@app.post("/v1/charge")
async def v1_charge(request: Request) -> Response:
    body = await _get_json_silent(request) or {}
    user_id = body.get("user_id")
    amount = body.get("amount")

    if not user_id:
        return _v1_headers(_json_response({"ok": False, "error": "user_id required"}, 200))
    if not isinstance(amount, int):
        return _v1_headers(_json_response({"ok": False, "error": "amount must be an integer"}, 200))
    balance = _BALANCES.get(user_id)
    if balance is None:
        return _v1_headers(_json_response({"ok": False, "error": "unknown user"}, 200))
    if amount > balance:
        return _v1_headers(_json_response({"ok": False, "error": "insufficient funds"}, 200))
    return _v1_headers(_json_response({"ok": True, "remaining": balance - amount}, 200))


@app.post("/v2/charge")
async def v2_charge(request: Request) -> Response:
    body = await _get_json_silent(request) or {}
    if "user_id" not in body:
        return _json_response({"message": "user_id required", "field": "user_id"}, 422)
    amount = body.get("amount")
    if not isinstance(amount, int):
        return _json_response({"message": "amount must be an integer", "field": "amount"}, 422)
    balance = _BALANCES.get(body["user_id"])
    if balance is None:
        return _json_response({"message": "unknown user"}, 404)
    if amount > balance:
        return _json_response({"message": "insufficient funds", "balance": balance}, 402)
    return _json_response({"remaining": balance - amount}, 200)


@app.get("/v1/ping")
def v1_ping() -> Response:
    return _v1_headers(Response(content="pong", status_code=200, media_type="text/html"))


@app.get("/v2/ping")
def v2_ping() -> Response:
    return _json_response("pong", 200)


@app.post("/v2/batch")
async def v2_batch(request: Request) -> Response:
    body = await _get_json_silent(request)
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

    failures = sum(1 for outcome in outcomes if not outcome["ok"])
    status = 200 if failures == 0 else 207
    return _json_response({"outcomes": outcomes, "failures": failures}, status)


@app.get("/v1/config")
def v1_config() -> Response:
    return _v1_headers(
        _json_response(
            {
                "deprecation": DEPRECATION,
                "deprecated": True,
                "isDeprecated": True,
                "tiers": ["free", "pro"],
            },
            200,
        )
    )