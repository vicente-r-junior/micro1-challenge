"""Small inventory service. Synthetic case, written for this benchmark.

Exercises: JSON body handling, manual validation with explicit 400s, a query
parameter with a default, path converters, and 404 on a missing resource.
"""

from flask import Flask, jsonify, request

app = Flask(__name__)
app.config["PAGE_SIZE"] = 2

_ITEMS = {
    1: {"id": 1, "name": "bolt", "qty": 40},
    2: {"id": 2, "name": "nut", "qty": 12},
    3: {"id": 3, "name": "washer", "qty": 7},
}


@app.route("/items", methods=["GET"])
def list_items():
    limit = request.args.get("limit", type=int) or app.config["PAGE_SIZE"]
    items = list(_ITEMS.values())[:limit]
    return jsonify({"items": items, "count": len(items)})


@app.route("/items/<int:item_id>", methods=["GET"])
def get_item(item_id):
    item = _ITEMS.get(item_id)
    if item is None:
        return jsonify({"error": "item not found"}), 404
    return jsonify(item)


@app.route("/items", methods=["POST"])
def create_item():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "body must be JSON"}), 400
    if "name" not in data:
        return jsonify({"error": "name is required"}), 400
    if not isinstance(data["name"], str):
        return jsonify({"error": "name must be a string"}), 400
    qty = data.get("qty", 0)
    new_id = max(_ITEMS) + 1
    return jsonify({"id": new_id, "name": data["name"], "qty": qty}), 201


@app.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    if item_id not in _ITEMS:
        return jsonify({"error": "item not found"}), 404
    return jsonify({"deleted": item_id})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "page_size": app.config["PAGE_SIZE"]})
