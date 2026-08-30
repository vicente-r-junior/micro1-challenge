"""Bulk endpoint returning multi-status. Synthetic case for this benchmark.

Exercises: a JSON *array* request body (not an object), per-item outcomes, HTTP
207, and a partial-failure path that still returns 2xx.
"""

from flask import Flask, jsonify, request

app = Flask(__name__)

_KNOWN = {"a", "b", "c"}


@app.route("/bulk/verify", methods=["POST"])
def bulk_verify():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "body must be JSON"}), 400
    if not isinstance(payload, list):
        return jsonify({"error": "body must be a JSON array"}), 400
    if not payload:
        return jsonify({"error": "array must not be empty"}), 400

    results = []
    for index, key in enumerate(payload):
        if not isinstance(key, str):
            results.append({"index": index, "status": "invalid", "reason": "not a string"})
        elif key in _KNOWN:
            results.append({"index": index, "status": "ok"})
        else:
            results.append({"index": index, "status": "unknown"})

    failed = sum(1 for r in results if r["status"] != "ok")
    status = 200 if failed == 0 else 207
    return jsonify({"results": results, "failed": failed}), status


@app.route("/bulk/limits", methods=["GET"])
def limits():
    return jsonify({"max_items": 100, "known": sorted(_KNOWN)})
