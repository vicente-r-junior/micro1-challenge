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

from flask import Flask, jsonify, make_response, request

app = Flask(__name__)

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
    # `terminal` is computed on read and stored nowhere. A migration that maps
    # the stored dict onto a response model drops it silently.
    return {**order, "terminal": order["state"] in TERMINAL}


@app.route("/orders/<order_id>", methods=["GET"])
def get_order(order_id):
    order = _ORDERS.get(order_id)
    if order is None:
        return jsonify({"error": "order not found", "id": order_id}), 404
    return jsonify(_present(order))


@app.route("/orders", methods=["POST"])
def create_order():
    body = request.get_json(silent=True) or {}
    total = body.get("total")
    if not isinstance(total, int) or total <= 0:
        return jsonify({"error": "total must be a positive integer"}), 400

    key = request.headers.get("Idempotency-Key")
    if key:
        seen = _IDEMPOTENCY.get(key)
        if seen is not None:
            if seen["total"] != total:
                return jsonify({
                    "error": "idempotency key reused with a different body",
                    "code": "IDEMPOTENCY_MISMATCH",
                }), 422
            # Replay: the original resource, and 200 rather than 201.
            return jsonify(_present(_ORDERS[seen["id"]])), 200

    order_id = f"o{_NEXT[0]}"
    _NEXT[0] += 1
    order = {"id": order_id, "state": "draft", "total": total, "lines": body.get("lines", 1)}
    _ORDERS[order_id] = order
    if key:
        _IDEMPOTENCY[key] = {"id": order_id, "total": total}

    response = make_response(jsonify(_present(order)), 201)
    response.headers["Location"] = f"/orders/{order_id}"
    return response


@app.route("/orders/<order_id>/transition", methods=["POST"])
def transition(order_id):
    order = _ORDERS.get(order_id)
    if order is None:
        return jsonify({"error": "order not found", "id": order_id}), 404

    body = request.get_json(silent=True) or {}
    target = body.get("to")
    if not target:
        return jsonify({"error": "to is required"}), 400
    if target not in TRANSITIONS:
        # Not a state at all: the client sent nonsense.
        return jsonify({"error": "unknown state", "state": target}), 400

    allowed = TRANSITIONS[order["state"]]
    if target not in allowed:
        # A real state, just not reachable from here.
        return jsonify({
            "error": "illegal transition",
            "from": order["state"],
            "to": target,
            "allowed": allowed,
        }), 409

    order["state"] = target
    return jsonify(_present(order))


@app.route("/orders/<order_id>", methods=["DELETE"])
def delete_order(order_id):
    order = _ORDERS.get(order_id)
    if order is None:
        return jsonify({"error": "order not found", "id": order_id}), 404
    if order["state"] != "draft":
        return jsonify({
            "error": "only draft orders can be deleted",
            "state": order["state"],
            "code": "NOT_DELETABLE",
        }), 409
    return "", 204


@app.route("/orders", methods=["GET"])
def list_orders():
    state = request.args.get("state")
    rows = list(_ORDERS.values())
    if state:
        if state not in TRANSITIONS:
            return jsonify({"error": "unknown state", "state": state}), 400
        rows = [o for o in rows if o["state"] == state]
    return jsonify({"orders": [_present(o) for o in rows], "count": len(rows)})
