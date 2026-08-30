"""Order lifecycle with idempotency migrated from Flask to FastAPI."""

import json
from typing import Any, Dict, Optional

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, computed_field

app = FastAPI()

TRANSITIONS = {
    "draft": ["submitted", "cancelled"],
    "submitted": ["approved", "rejected", "cancelled"],
    "approved": ["fulfilled"],
    "rejected": [],
    "cancelled": [],
    "fulfilled": [],
}
TERMINAL = {"rejected", "cancelled", "fulfilled"}

_ORDERS: Dict[str, Dict[str, Any]] = {
    "o1": {"id": "o1", "state": "draft", "total": 30, "lines": 2},
    "o2": {"id": "o2", "state": "approved", "total": 90, "lines": 5},
}
_IDEMPOTENCY: Dict[str, Dict[str, Any]] = {}
_NEXT = [3]


class OrderPresentation(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Any
    state: Any
    total: Any
    lines: Any

    @computed_field
    @property
    def terminal(self) -> bool:
        return self.state in TERMINAL


def _present(order: Dict[str, Any]) -> Dict[str, Any]:
    # `terminal` is computed on read and stored nowhere.
    return OrderPresentation.model_validate(order).model_dump()


def _is_json_content_type(content_type: str) -> bool:
    mimetype = content_type.split(";", 1)[0].strip().lower()
    return mimetype == "application/json" or (
        mimetype.startswith("application/") and mimetype.endswith("+json")
    )


async def _get_json_silent(request: Request) -> Any:
    # Mirrors Flask's request.get_json(silent=True): if the request is not JSON,
    # or if parsing fails, behave as though there was no JSON body.
    if not _is_json_content_type(request.headers.get("content-type", "")):
        return {}
    try:
        return await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


@app.get("/orders/{order_id}")
async def get_order(order_id: str) -> JSONResponse:
    order = _ORDERS.get(order_id)
    if order is None:
        return JSONResponse({"error": "order not found", "id": order_id}, status_code=404)
    return JSONResponse(_present(order))


@app.post("/orders")
async def create_order(request: Request) -> JSONResponse:
    body = await _get_json_silent(request) or {}
    total = body.get("total")
    if not isinstance(total, int) or total <= 0:
        return JSONResponse({"error": "total must be a positive integer"}, status_code=400)

    key = request.headers.get("Idempotency-Key")
    if key:
        seen = _IDEMPOTENCY.get(key)
        if seen is not None:
            if seen["total"] != total:
                return JSONResponse(
                    {
                        "error": "idempotency key reused with a different body",
                        "code": "IDEMPOTENCY_MISMATCH",
                    },
                    status_code=422,
                )
            # Replay: the original resource, and 200 rather than 201.
            return JSONResponse(_present(_ORDERS[seen["id"]]), status_code=200)

    order_id = f"o{_NEXT[0]}"
    _NEXT[0] += 1
    order = {
        "id": order_id,
        "state": "draft",
        "total": total,
        "lines": body.get("lines", 1),
    }
    _ORDERS[order_id] = order
    if key:
        _IDEMPOTENCY[key] = {"id": order_id, "total": total}

    return JSONResponse(
        _present(order),
        status_code=201,
        headers={"Location": f"/orders/{order_id}"},
    )


@app.post("/orders/{order_id}/transition")
async def transition(order_id: str, request: Request) -> JSONResponse:
    order = _ORDERS.get(order_id)
    if order is None:
        return JSONResponse({"error": "order not found", "id": order_id}, status_code=404)

    body = await _get_json_silent(request) or {}
    target = body.get("to")
    if not target:
        return JSONResponse({"error": "to is required"}, status_code=400)
    if target not in TRANSITIONS:
        # Not a state at all: the client sent nonsense.
        return JSONResponse({"error": "unknown state", "state": target}, status_code=400)

    allowed = TRANSITIONS[order["state"]]
    if target not in allowed:
        # A real state, just not reachable from here.
        return JSONResponse(
            {
                "error": "illegal transition",
                "from": order["state"],
                "to": target,
                "allowed": allowed,
            },
            status_code=409,
        )

    order["state"] = target
    return JSONResponse(_present(order))


@app.delete("/orders/{order_id}")
async def delete_order(order_id: str) -> Response:
    order = _ORDERS.get(order_id)
    if order is None:
        return JSONResponse({"error": "order not found", "id": order_id}, status_code=404)
    if order["state"] != "draft":
        return JSONResponse(
            {
                "error": "only draft orders can be deleted",
                "state": order["state"],
                "code": "NOT_DELETABLE",
            },
            status_code=409,
        )
    return Response(status_code=204)


@app.get("/orders")
async def list_orders(state: Optional[str] = Query(default=None)) -> JSONResponse:
    rows = list(_ORDERS.values())
    if state:
        if state not in TRANSITIONS:
            return JSONResponse({"error": "unknown state", "state": state}, status_code=400)
        rows = [order for order in rows if order["state"] == state]
    return JSONResponse({"orders": [_present(order) for order in rows], "count": len(rows)})