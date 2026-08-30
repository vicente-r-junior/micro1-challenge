from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, conint
from typing import Optional, List, Dict

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

_ORDERS: Dict[str, Dict] = {
    "o1": {"id": "o1", "state": "draft", "total": 30, "lines": 2},
    "o2": {"id": "o2", "state": "approved", "total": 90, "lines": 5},
}
_IDEMPOTENCY: Dict[str, Dict] = {}
_NEXT = [3]

class OrderCreate(BaseModel):
    total: conint(gt=0)
    lines: Optional[int] = 1

class OrderResponse(BaseModel):
    id: str
    state: str
    total: int
    lines: int
    terminal: bool

def _present(order: Dict) -> OrderResponse:
    return OrderResponse(**{**order, "terminal": order["state"] in TERMINAL})

@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str):
    order = _ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail={"error": "order not found", "id": order_id})
    return _present(order)

@app.post("/orders", response_model=OrderResponse, status_code=201)
async def create_order(order_create: OrderCreate, idempotency_key: Optional[str] = Header(None)):
    total = order_create.total
    if idempotency_key:
        seen = _IDEMPOTENCY.get(idempotency_key)
        if seen is not None:
            if seen["total"] != total:
                raise HTTPException(status_code=422, detail={
                    "error": "idempotency key reused with a different body",
                    "code": "IDEMPOTENCY_MISMATCH",
                })
            return _present(_ORDERS[seen["id"]])

    order_id = f"o{_NEXT[0]}"
    _NEXT[0] += 1
    order = {"id": order_id, "state": "draft", "total": total, "lines": order_create.lines}
    _ORDERS[order_id] = order
    if idempotency_key:
        _IDEMPOTENCY[idempotency_key] = {"id": order_id, "total": total}

    response = JSONResponse(content=_present(order))
    response.headers["Location"] = f"/orders/{order_id}"
    return response

@app.post("/orders/{order_id}/transition", response_model=OrderResponse)
async def transition(order_id: str, target: str):
    order = _ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail={"error": "order not found", "id": order_id})

    if not target:
        raise HTTPException(status_code=400, detail={"error": "to is required"})
    if target not in TRANSITIONS:
        raise HTTPException(status_code=400, detail={"error": "unknown state", "state": target})

    allowed = TRANSITIONS[order["state"]]
    if target not in allowed:
        raise HTTPException(status_code=409, detail={
            "error": "illegal transition",
            "from": order["state"],
            "to": target,
            "allowed": allowed,
        })

    order["state"] = target
    return _present(order)

@app.delete("/orders/{order_id}")
async def delete_order(order_id: str):
    order = _ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail={"error": "order not found", "id": order_id})
    if order["state"] != "draft":
        raise HTTPException(status_code=409, detail={
            "error": "only draft orders can be deleted",
            "state": order["state"],
            "code": "NOT_DELETABLE",
        })
    return JSONResponse(status_code=204)

@app.get("/orders")
async def list_orders(state: Optional[str] = None):
    rows = list(_ORDERS.values())
    if state:
        if state not in TRANSITIONS:
            raise HTTPException(status_code=400, detail={"error": "unknown state", "state": state})
        rows = [o for o in rows if o["state"] == state]
    return {"orders": [_present(o) for o in rows], "count": len(rows)}