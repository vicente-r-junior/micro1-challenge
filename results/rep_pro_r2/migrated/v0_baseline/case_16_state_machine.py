"""Order lifecycle with idempotency. Synthetic case for this benchmark.

Behaviour that lives in the handler rather than in the schema, which is exactly
the kind a type-driven rewrite loses:

  * an Idempotency-Key header makes a repeated create return the *original*
    resource with 200 instead of 201, and a reused key with a different body is
    a 422 with a specific code
  * transitions are validated against a table; an illegal one is a 409 that
    lists what would have been legal
  * delete is only allowed from "draft"; anywhere else is 409, not 405
  * the response carries a computed field that is not stored anywhere
  * an unknown transition target is 400, while a known-but-illegal one is 409 --
    two different statuses for what looks like the same mistake
"""

import json
from typing import Optional

from fastapi import FastAPI, Header, Query, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

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

_ORDERS = {
    "o1": {"id": "o1", "state": "draft", "total": 30, "lines": 2},
    "o2": {"id": "o2", "state": "approved", "total": 90, "lines": 5},
}
_IDEMPOTENCY = {}
_NEXT = [3]


class PresentOrder(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    state: str
    total: int
    terminal: bool


def _present(order):
    return PresentOrder(**order, terminal=order["state"] in TERMINAL).model_dump()


async def _json_body(request: Request):
    raw = await request.body()
    if not raw:
        return {}
    try:
        return json.loads(raw) or {}
    except json.JSONDecodeError:
        return {}


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    order = _ORDERS.get(order_id)
    if order is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "order not found", "id": order_id},
        )
    return _present(order)


@app.post("/orders")
async def create_order(
    request: Request,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    body = await _json_body(request)
    total = body.get("total")
    if not isinstance(total, int) or total <= 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "total must be a positive integer"},
        )

    key = idempotency_key
    if key:
        seen = _IDEMPOTENCY.get(key)
        if seen is not None:
            if seen["total"] != total:
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={
                        "error": "idempotency key reused with a different body",
                        "code": "IDEMPOTENCY_MISMATCH",
                    },
                )
            return _present(_ORDERS[seen["id"]])

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
        status_code=status.HTTP_201_CREATED,
        content=_present(order),
        headers={"Location": f"/orders/{order_id}"},
    )


@app.post("/orders/{order_id}/transition")
async def transition(order_id: str, request: Request):
    order = _ORDERS.get(order_id)
    if order is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "order not found", "id": order_id},
        )

    body = await _json_body(request)
    target = body.get("to")
    if not target:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "to is required"},
        )
    if target not in TRANSITIONS:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "unknown state", "state": target},
        )

    allowed = TRANSITIONS[order["state"]]
    if target not in allowed:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "illegal transition",
                "from": order["state"],
                "to": target,
                "allowed": allowed,
            },
        )

    order["state"] = target
    return _present(order)


@app.delete("/orders/{order_id}")
async def delete_order(order_id: str):
    order = _ORDERS.get(order_id)
    if order is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "order not found", "id": order_id},
        )
    if order["state"] != "draft":
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "only draft orders can be deleted",
                "state": order["state"],
                "code": "NOT_DELETABLE",
            },
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/orders")
async def list_orders(state: Optional[str] = Query(default=None)):
    rows = list(_ORDERS.values())
    if state:
        if state not in TRANSITIONS:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "unknown state", "state": state},
            )
        rows = [o for o in rows if o["state"] == state]
    return {"orders": [_present(o) for o in rows], "count": len(rows)}