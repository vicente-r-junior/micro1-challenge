"""A gateway that grew over six years. Synthetic case for this benchmark.

This is the shape legacy code actually has: three generations of error handling
living side by side because each was added by a different person under a
different deadline, and clients were written against whichever one existed at
the time.

Nothing here is good design. That is the point. A migration is not allowed to
tidy it up, because every inconsistency below is load-bearing for somebody.

Traps, in order of how often a rewrite normalises them away:
  * three different error envelopes: {"error": ...}, {"message": ...}, and a
    bare string body
  * /v1/charge answers 200 with an error payload -- the status is a lie, and a
    client checks the body
  * /v1/users/<id> returns 200 with an empty object for a missing user, while
    /v2/users/<id> returns a proper 404
  * a deprecation header only on the v1 routes
  * a status that depends on a computed value (207 vs 200)
  * an endpoint that returns a JSON string, not a JSON object
"""

from flask import Flask, jsonify, make_response, request

app = Flask(__name__)

_USERS = {"u1": {"id": "u1", "name": "ana", "tier": "pro"}}
_BALANCES = {"u1": 50}
DEPRECATION = "version=1; sunset=2027-01-01"


def _v1_headers(response):
    response.headers["X-API-Deprecation"] = DEPRECATION
    return response


@app.route("/v1/users/<user_id>", methods=["GET"])
def v1_get_user(user_id):
    # The original author decided "not found" was an empty object with a 200.
    # Clients now test `if not payload`. A 404 would break every one of them.
    user = _USERS.get(user_id, {})
    return _v1_headers(make_response(jsonify(user), 200))


@app.route("/v2/users/<user_id>", methods=["GET"])
def v2_get_user(user_id):
    user = _USERS.get(user_id)
    if user is None:
        return jsonify({"message": "user not found"}), 404
    return jsonify({"data": user})


@app.route("/v1/charge", methods=["POST"])
def v1_charge():
    body = request.get_json(silent=True) or {}
    user_id = body.get("user_id")
    amount = body.get("amount")

    # Generation one: always 200, the caller reads "ok".
    if not user_id:
        return _v1_headers(make_response(jsonify({"ok": False, "error": "user_id required"}), 200))
    if not isinstance(amount, int):
        return _v1_headers(make_response(jsonify({"ok": False, "error": "amount must be an integer"}), 200))
    balance = _BALANCES.get(user_id)
    if balance is None:
        return _v1_headers(make_response(jsonify({"ok": False, "error": "unknown user"}), 200))
    if amount > balance:
        return _v1_headers(make_response(jsonify({"ok": False, "error": "insufficient funds"}), 200))
    return _v1_headers(make_response(jsonify({"ok": True, "remaining": balance - amount}), 200))


@app.route("/v2/charge", methods=["POST"])
def v2_charge():
    body = request.get_json(silent=True) or {}
    if "user_id" not in body:
        return jsonify({"message": "user_id required", "field": "user_id"}), 422
    amount = body.get("amount")
    if not isinstance(amount, int):
        return jsonify({"message": "amount must be an integer", "field": "amount"}), 422
    balance = _BALANCES.get(body["user_id"])
    if balance is None:
        return jsonify({"message": "unknown user"}), 404
    if amount > balance:
        return jsonify({"message": "insufficient funds", "balance": balance}), 402
    return jsonify({"remaining": balance - amount}), 200


@app.route("/v1/ping", methods=["GET"])
def v1_ping():
    # Generation zero: a bare string. Not JSON, no object wrapper.
    return _v1_headers(make_response("pong", 200))


@app.route("/v2/ping", methods=["GET"])
def v2_ping():
    # Valid JSON, but a scalar rather than an object.
    return jsonify("pong")


@app.route("/v2/batch", methods=["POST"])
def v2_batch():
    body = request.get_json(silent=True)
    if not isinstance(body, list):
        return jsonify({"message": "body must be a JSON array"}), 422

    outcomes = []
    for index, entry in enumerate(body):
        if not isinstance(entry, dict) or "user_id" not in entry:
            outcomes.append({"index": index, "ok": False, "error": "malformed entry"})
        elif entry["user_id"] not in _USERS:
            outcomes.append({"index": index, "ok": False, "error": "unknown user"})
        else:
            outcomes.append({"index": index, "ok": True})

    failures = sum(1 for o in outcomes if not o["ok"])
    # 207 only when the batch is mixed; all-fail is still 207, all-ok is 200.
    status = 200 if failures == 0 else 207
    return jsonify({"outcomes": outcomes, "failures": failures}), status


@app.route("/v1/config", methods=["GET"])
def v1_config():
    # Two spellings of the same value, kept because a client reads each one.
    return _v1_headers(make_response(jsonify({
        "deprecation": DEPRECATION,
        "deprecated": True,
        "isDeprecated": True,
        "tiers": ["free", "pro"],
    }), 200))
