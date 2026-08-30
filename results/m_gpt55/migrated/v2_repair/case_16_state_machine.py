"""FastAPI migration of the legacy Flask order lifecycle module."""

import json
from typing import Any, Dict, List, Optional, Set

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict

app = FastAPI(redirect_slashes=False)

TRANSITIONS = {
    "draft": ["submitted", "cancelled"],
    "submitted": ["approved", "rejected", "cancelled"],
    "approved": ["fulfilled"],
    "rejected": [],
    "cancelled": [],
    "fulfilled": [],
}
TERMINAL = {"rejected", "cancelled", "fulfilled"}

_ORDERS = {
    "o1": {"id": "o1", "state": "draft", "total": 30, "lines": 2},
    "o2": {"id": "o2", "state": "approved", "total": 90, "lines": 5},
}
_IDEMPOTENCY = {}
_NEXT = [3]


class Settings(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    transitions: Dict[str, List[str]]
    terminal: Set[str]


_SETTINGS = Settings(transitions=TRANSITIONS, terminal=TERMINAL)


def get_settings() -> Settings:
    return _SETTINGS


class FlaskJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return (
            json.dumps(
                content,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")


def jsonify(content: Any, status_code: int = 200, headers: Optional[Dict[str, str]] = None) -> FlaskJSONResponse:
    return FlaskJSONResponse(content=content, status_code=status_code, headers=headers)


def _is_json_content_type(content_type: Optional[str]) -> bool:
    if not content_type:
        return False
    mimetype = content_type.split(";", 1)[0].strip().lower()
    return mimetype == "application/json" or (
        mimetype.startswith("application/") and mimetype.endswith("+json")
    )


async def _get_json_silent(request: Request) -> Any:
    if not _is_json_content_type(request.headers.get("content-type")):
        return None
    try:
        body = await request.body()
        return json.loads(body)
    except Exception:
        return None


def _first_query_arg(request: Request, name: str) -> Optional[str]:
    values = request.query_params.getlist(name)
    return values[0] if values else None


def _present(order: Dict[str, Any], settings: Settings) -> Dict[str, Any]:
    return {**order, "terminal": order["state"] in settings.terminal}


@app.get("/orders/{order_id}")
def get_order(order_id: str, settings: Settings = Depends(get_settings)):
    order = _ORDERS.get(order_id)
    if order is None:
        return jsonify({"error": "order not found", "id": order_id}, 404)
    return jsonify(_present(order, settings))


@app.post("/orders")
async def create_order(request: Request, settings: Settings = Depends(get_settings)):
    body = await _get_json_silent(request) or {}
    total = body.get("total")
    if not isinstance(total, int) or total <= 0:
        return jsonify({"error": "total must be a positive integer"}, 400)

    key = request.headers.get("Idempotency-Key")
    if key:
        seen = _IDEMPOTENCY.get(key)
        if seen is not None:
            if seen["total"] != total:
                return jsonify(
                    {
                        "error": "idempotency key reused with a different body",
                        "code": "IDEMPOTENCY_MISMATCH",
                    },
                    422,
                )
            return jsonify(_present(_ORDERS[seen["id"]], settings), 200)

    order_id = f"o{_NEXT[0]}"
    _NEXT[0] += 1
    order = {"id": order_id, "state": "draft", "total": total, "lines": body.get("lines", 1)}
    _ORDERS[order_id] = order
    if key:
        _IDEMPOTENCY[key] = {"id": order_id, "total": total}

    return jsonify(_present(order, settings), 201, headers={"Location": f"/orders/{order_id}"})


@app.post("/orders/{order_id}/transition")
async def transition(order_id: str, request: Request, settings: Settings = Depends(get_settings)):
    order = _ORDERS.get(order_id)
    if order is None:
        return jsonify({"error": "order not found", "id": order_id}, 404)

    body = await _get_json_silent(request) or {}
    target = body.get("to")
    if not target:
        return jsonify({"error": "to is required"}, 400)
    if target not in settings.transitions:
        return jsonify({"error": "unknown state", "state": target}, 400)

    allowed = settings.transitions[order["state"]]
    if target not in allowed:
        return jsonify(
            {
                "error": "illegal transition",
                "from": order["state"],
                "to": target,
                "allowed": allowed,
            },
            409,
        )

    order["state"] = target
    return jsonify(_present(order, settings))


@app.delete("/orders/{order_id}")
def delete_order(order_id: str):
    order = _ORDERS.get(order_id)
    if order is None:
        return jsonify({"error": "order not found", "id": order_id}, 404)
    if order["state"] != "draft":
        return jsonify(
            {
                "error": "only draft orders can be deleted",
                "state": order["state"],
                "code": "NOT_DELETABLE",
            },
            409,
        )
    return Response(content="", status_code=204, media_type="text/html")


@app.get("/orders")
def list_orders(request: Request, settings: Settings = Depends(get_settings)):
    state = _first_query_arg(request, "state")
    rows = list(_ORDERS.values())
    if state:
        if state not in settings.transitions:
            return jsonify({"error": "unknown state", "state": state}, 400)
        rows = [o for o in rows if o["state"] == state]
    return jsonify({"orders": [_present(o, settings) for o in rows], "count": len(rows)})