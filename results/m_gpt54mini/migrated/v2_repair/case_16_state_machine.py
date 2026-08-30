from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

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


def _present(order):
    return {**order, "terminal": order["state"] in TERMINAL}


@app.api_route("/orders/{order_id}", methods=["GET"])
async def get_order(order_id: str):
    order = _ORDERS.get(order_id)
    if order is None:
        return JSONResponse(content={"error": "order not found", "id": order_id}, status_code=404)
    return JSONResponse(content=_present(order))


@app.post("/orders")
async def create_order(request: Request):
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    total = body.get("total")
    if not isinstance(total, int) or total <= 0:
        return JSONResponse(content={"error": "total must be a positive integer"}, status_code=400)

    key = request.headers.get("Idempotency-Key")
    if key:
        seen = _IDEMPOTENCY.get(key)
        if seen is not None:
            if seen["total"] != total:
                return JSONResponse(content={"error": "idempotency key reused with a different body", "code": "IDEMPOTENCY_MISMATCH"}, status_code=422)
            return JSONResponse(content=_present(_ORDERS[seen["id"]]), status_code=200)

    order_id = f"o{_NEXT[0]}"
    _NEXT[0] += 1
    order = {"id": order_id, "state": "draft", "total": total, "lines": body.get("lines", 1)}
    _ORDERS[order_id] = order
    if key:
        _IDEMPOTENCY[key] = {"id": order_id, "total": total}

    return JSONResponse(content=_present(order), status_code=201, headers={"Location": f"/orders/{order_id}"})


@app.api_route("/orders/{order_id}/transition", methods=["POST"])
async def transition(order_id: str, request: Request):
    order = _ORDERS.get(order_id)
    if order is None:
        return JSONResponse(content={"error": "order not found", "id": order_id}, status_code=404)

    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    target = body.get("to")
    if not target:
        return JSONResponse(content={"error": "to is required"}, status_code=400)
    if target not in TRANSITIONS:
        return JSONResponse(content={"error": "unknown state", "state": target}, status_code=400)

    allowed = TRANSITIONS[order["state"]]
    if target not in allowed:
        return JSONResponse(content={"error": "illegal transition", "from": order["state"], "to": target, "allowed": allowed}, status_code=409)

    order["state"] = target
    return JSONResponse(content=_present(order))


@app.api_route("/orders/{order_id}", methods=["DELETE"])
async def delete_order(order_id: str):
    order = _ORDERS.get(order_id)
    if order is None:
        return JSONResponse(content={"error": "order not found", "id": order_id}, status_code=404)
    if order["state"] != "draft":
        return JSONResponse(content={"error": "only draft orders can be deleted", "state": order["state"], "code": "NOT_DELETABLE"}, status_code=409)
    return Response(content="", status_code=204)


@app.api_route("/orders", methods=["GET"])
async def list_orders(request: Request):
    state = request.query_params.get("state")
    rows = list(_ORDERS.values())
    if state:
        if state not in TRANSITIONS:
            return JSONResponse(content={"error": "unknown state", "state": state}, status_code=400)
        rows = [o for o in rows if o["state"] == state]
    return JSONResponse(content={"orders": [_present(o) for o in rows], "count": len(rows)})
