import json
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

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


def _present(order):
    return {**order, "terminal": order["state"] in TERMINAL}


async def _read_json_object(request: Request):
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type != "application/json" and not content_type.endswith("+json"):
        return {}
    raw = await request.body()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


@app.get("/orders")
async def list_orders(request: Request):
    state = request.query_params.get("state")
    rows = list(_ORDERS.values())
    if state:
        if state not in TRANSITIONS:
            return JSONResponse(content={"error": "unknown state", "state": state}, status_code=400)
        rows = [o for o in rows if o["state"] == state]
    return JSONResponse(content={"orders": [_present(o) for o in rows], "count": len(rows)})


@app.post("/orders")
async def create_order(request: Request):
    body = await _read_json_object(request)
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

    return JSONResponse(content=_present(order), status_code=201, headers={"Location": f"/orders/{order_id}"})


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    order = _ORDERS.get(order_id)
    if order is None:
        return JSONResponse(content={"error": "order not found", "id": order_id}, status_code=404)
    return JSONResponse(content=_present(order))


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
    return Response(status_code=204)


@app.post("/orders/{order_id}/transition")
async def transition(order_id: str, request: Request):
    order = _ORDERS.get(order_id)
    if order is None:
        return JSONResponse(content={"error": "order not found", "id": order_id}, status_code=404)

    body = await _read_json_object(request)
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
    return JSONResponse(content=_present(order))