from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Optional

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
_IDEMPOTENCY: dict[str, dict[str, Any]] = {}
_NEXT = [3]


class Order(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    state: str
    total: int
    lines: int
    terminal: bool


class OrderCreate(BaseModel):
    total: int
    lines: int = 1


class TransitionRequest(BaseModel):
    to: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    id: Optional[str] = None
    code: Optional[str] = None
    state: Optional[str] = None
    from_: Optional[str] = Field(default=None, alias="from")
    to: Optional[str] = None
    allowed: Optional[list[str]] = None

    model_config = ConfigDict(populate_by_name=True)


class OrdersListResponse(BaseModel):
    orders: list[Order]
    count: int


def _present(order: dict[str, Any]) -> dict[str, Any]:
    return {**order, "terminal": order["state"] in TERMINAL}


@app.get("/orders/{order_id}", response_model=Order, responses={404: {"model": ErrorResponse}})
def get_order(order_id: str):
    order = _ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail={"error": "order not found", "id": order_id})
    return _present(order)


@app.post(
    "/orders",
    response_model=Order,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_order(request: Request, body: OrderCreate):
    total = body.total
    if not isinstance(total, int) or total <= 0:
        raise HTTPException(status_code=400, detail={"error": "total must be a positive integer"})

    key = request.headers.get("Idempotency-Key")
    if key:
        seen = _IDEMPOTENCY.get(key)
        if seen is not None:
            if seen["total"] != total:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "idempotency key reused with a different body",
                        "code": "IDEMPOTENCY_MISMATCH",
                    },
                )
            return _present(_ORDERS[seen["id"]])

    order_id = f"o{_NEXT[0]}"
    _NEXT[0] += 1
    order = {"id": order_id, "state": "draft", "total": total, "lines": body.lines}
    _ORDERS[order_id] = order
    if key:
        _IDEMPOTENCY[key] = {"id": order_id, "total": total}

    return Response(
        content=Order.model_validate(_present(order)).model_dump_json(),
        status_code=201,
        media_type="application/json",
        headers={"Location": f"/orders/{order_id}"},
    )


@app.post("/orders/{order_id}/transition", response_model=Order)
def transition(order_id: str, body: TransitionRequest):
    order = _ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail={"error": "order not found", "id": order_id})

    target = body.to
    if not target:
        raise HTTPException(status_code=400, detail={"error": "to is required"})
    if target not in TRANSITIONS:
        raise HTTPException(status_code=400, detail={"error": "unknown state", "state": target})

    allowed = TRANSITIONS[order["state"]]
    if target not in allowed:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "illegal transition",
                "from": order["state"],
                "to": target,
                "allowed": allowed,
            },
        )

    order["state"] = target
    return _present(order)


@app.delete("/orders/{order_id}", status_code=204)
def delete_order(order_id: str):
    order = _ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail={"error": "order not found", "id": order_id})
    if order["state"] != "draft":
        raise HTTPException(
            status_code=409,
            detail={
                "error": "only draft orders can be deleted",
                "state": order["state"],
                "code": "NOT_DELETABLE",
            },
        )
    return Response(status_code=204)


@app.get("/orders", response_model=OrdersListResponse, responses={400: {"model": ErrorResponse}})
def list_orders(state: Optional[str] = None):
    rows = list(_ORDERS.values())
    if state:
        if state not in TRANSITIONS:
            raise HTTPException(status_code=400, detail={"error": "unknown state", "state": state})
        rows = [o for o in rows if o["state"] == state]
    return {"orders": [_present(o) for o in rows], "count": len(rows)}