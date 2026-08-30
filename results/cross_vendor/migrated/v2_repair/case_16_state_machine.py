from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

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

class CreateOrderRequest(BaseModel):
    total: int = Field(..., gt=0)
    lines: Optional[int] = 1

class TransitionRequest(BaseModel):
    to: str

def _present(order: Dict[str, Any]) -> Dict[str, Any]:
    return {**order, "terminal": order["state"] in TERMINAL}

@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    order = _ORDERS.get(order_id)
    if order is None:
        return JSONResponse(content={"error": "order not found", "id": order_id}, status_code=404)
    return _present(order)

@app.post("/orders")
async def create_order(request: Request):
    body = await request.json() or {}
    total = body.get("total")
    if not isinstance(total, int) or total <= 0:
        return JSONResponse(content={"error": "total must be a positive integer"}, status_code=400)

    key = request.headers.get("Idempotency-Key")
    if key:
        seen = _IDEMPOTENCY.get(key)
        if seen is not None:
            if seen["total"] != total:
                return JSONResponse(content={
                    "error": "idempotency key reused with a different body",
                    "code": "IDEMPOTENCY_MISMATCH",
                }, status_code=422)
            return JSONResponse(content=_present(_ORDERS[seen["id"]]), status_code=200)

    order_id = f"o{_NEXT[0]}"
    _NEXT[0] += 1
    order = {"id": order_id, "state": "draft", "total": total, "lines": body.get("lines", 1)}
    _ORDERS[order_id] = order
    if key:
        _IDEMPOTENCY[key] = {"id": order_id, "total": total}

    response = JSONResponse(content=_present(order), status_code=201)
    response.headers["Location"] = f"/orders/{order_id}"
    return response

@app.post("/orders/{order_id}/transition")
async def transition(order_id: str, request: Request):
    order = _ORDERS.get(order_id)
    if order is None:
        return JSONResponse(content={"error": "order not found", "id": order_id}, status_code=404)

    body = await request.json() or {}
    target = body.get("to")
    if not target:
        return JSONResponse(content={"error": "to is required"}, status_code=400)
    if target not in TRANSITIONS:
        return JSONResponse(content={"error": "unknown state", "state": target}, status_code=400)

    allowed = TRANSITIONS[order["state"]]
    if target not in allowed:
        return JSONResponse(content={
            "error": "illegal transition",
            "from": order["state"],
            "to": target,
            "allowed": allowed,
        }, status_code=409)

    order["state"] = target
    return _present(order)

@app.delete("/orders/{order_id}")
async def delete_order(order_id: str):
    order = _ORDERS.get(order_id)
    if order is None:
        return JSONResponse(content={"error": "order not found", "id": order_id}, status_code=404)
    if order["state"] != "draft":
        return JSONResponse(content={
            "error": "only draft orders can be deleted",
            "state": order["state"],
            "code": "NOT_DELETABLE",
        }, status_code=409)
    return JSONResponse(content={}, status_code=204)

@app.get("/orders")
async def list_orders(state: Optional[str] = None):
    rows = list(_ORDERS.values())
    if state:
        if state not in TRANSITIONS:
            return JSONResponse(content={"error": "unknown state", "state": state}, status_code=400)
        rows = [o for o in rows if o["state"] == state]
    return {"orders": [_present(o) for o in rows], "count": len(rows)}