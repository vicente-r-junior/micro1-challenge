"""Query-string heavy search endpoint. Synthetic case for this benchmark.

Exercises: typed query parameters with defaults, getlist for repeated values,
a truthy-string boolean, and silent coercion failures.
"""

from flask import Flask, jsonify, request

app = Flask(__name__)

_PRODUCTS = [
    {"id": 1, "name": "bolt", "tag": "hardware", "price": 3},
    {"id": 2, "name": "nut", "tag": "hardware", "price": 1},
    {"id": 3, "name": "manual", "tag": "docs", "price": 0},
]


@app.route("/search", methods=["GET"])
def search():
    term = request.args.get("q", "")
    limit = request.args.get("limit", type=int)
    max_price = request.args.get("max_price", type=float)
    include_free = request.args.get("include_free", "false").lower() in ("1", "true", "yes")
    tags = request.args.getlist("tag")

    rows = [p for p in _PRODUCTS if term.lower() in p["name"].lower()]
    if tags:
        rows = [p for p in rows if p["tag"] in tags]
    if max_price is not None:
        rows = [p for p in rows if p["price"] <= max_price]
    if not include_free:
        rows = [p for p in rows if p["price"] > 0]
    if limit:
        rows = rows[:limit]
    return jsonify({"results": rows, "count": len(rows), "echo": {"q": term, "limit": limit}})


@app.route("/facets", methods=["GET"])
def facets():
    counts = {}
    for product in _PRODUCTS:
        counts[product["tag"]] = counts.get(product["tag"], 0) + 1
    return jsonify({"tags": counts})
