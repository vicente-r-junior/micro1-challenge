import json
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

_USERS = {"u1": {"id": "u1", "name": "ana", "tier": "pro"}}
_BALANCES = {"u1": 50}
DEPRECATION = "version=1; sunset=2027-01-01"


class AppConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    deprecation: str
    tiers: list[str]


_CONFIG = AppConfig(deprecation=DEPRECATION, tiers=["free", "pro"])


def get_config() -> AppConfig:
    return _CONFIG


class FlaskJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return (
            json.dumps(
                content,
                ensure_ascii=True,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")


def _json(content: Any, status_code: int = 200) -> FlaskJSONResponse:
    return FlaskJSONResponse(content=content, status_code=status_code)


def _v1_json(content: Any, status_code: int, config: AppConfig) -> FlaskJSONResponse:
    return FlaskJSONResponse(
        content=content,
        status_code=status_code,
        headers={"X-API-Deprecation": config.deprecation},
    )


def _is_json_content_type(content_type: str | None) -> bool:
    if not content_type:
        return False
    media_type = content_type.split(";", 1)[0].strip().lower()
    return media_type == "application/json" or (
        media_type.startswith("application/") and media_type.endswith("+json")
    )


async def _get_json_silent(request: Request) -> Any:
    if not _is_json_content_type(request.headers.get("content-type")):
        return None
    raw = await request.body()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return None


@app.get("/v1/users/{user_id}")
async def v1_get_user(user_id: str, config: AppConfig = Depends(get_config)):
    user = _USERS.get(user_id, {})
    return _v1_json(user, 200, config)


@app.get("/v2/users/{user_id}")
async def v2_get_user(user_id: str):
    user = _USERS.get(user_id)
    if user is None:
        return _json({"message": "user not found"}, 404)
    return _json({"data": user})


@app.post("/v1/charge")
async def v1_charge(request: Request, config: AppConfig = Depends(get_config)):
    body = await _get_json_silent(request) or {}
    user_id = body.get("user_id")
    amount = body.get("amount")

    if not user_id:
        return _v1_json({"ok": False, "error": "user_id required"}, 200, config)
    if not isinstance(amount, int):
        return _v1_json({"ok": False, "error": "amount must be an integer"}, 200, config)
    balance = _BALANCES.get(user_id)
    if balance is None:
        return _v1_json({"ok": False, "error": "unknown user"}, 200, config)
    if amount > balance:
        return _v1_json({"ok": False, "error": "insufficient funds"}, 200, config)
    return _v1_json({"ok": True, "remaining": balance - amount}, 200, config)


@app.post("/v2/charge")
async def v2_charge(request: Request):
    body = await _get_json_silent(request) or {}
    if "user_id" not in body:
        return _json({"message": "user_id required", "field": "user_id"}, 422)
    amount = body.get("amount")
    if not isinstance(amount, int):
        return _json({"message": "amount must be an integer", "field": "amount"}, 422)
    balance = _BALANCES.get(body["user_id"])
    if balance is None:
        return _json({"message": "unknown user"}, 404)
    if amount > balance:
        return _json({"message": "insufficient funds", "balance": balance}, 402)
    return _json({"remaining": balance - amount}, 200)


@app.get("/v1/ping")
async def v1_ping(config: AppConfig = Depends(get_config)):
    return Response(
        content="pong",
        status_code=200,
        media_type="text/html",
        headers={"X-API-Deprecation": config.deprecation},
    )


@app.get("/v2/ping")
async def v2_ping():
    return _json("pong")


@app.post("/v2/batch")
async def v2_batch(request: Request):
    body = await _get_json_silent(request)
    if not isinstance(body, list):
        return _json({"message": "body must be a JSON array"}, 422)

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
    return _json({"outcomes": outcomes, "failures": failures}, status)


@app.get("/v1/config")
async def v1_config(config: AppConfig = Depends(get_config)):
    return _v1_json(
        {
            "deprecation": config.deprecation,
            "deprecated": True,
            "isDeprecated": True,
            "tiers": config.tiers,
        },
        200,
        config,
    )