"""Responses that are not plain JSON. Synthetic case for this benchmark.

Exercises: make_response, text/plain and text/csv bodies, custom headers, a 204
with no content, and a redirect. Migrations tend to JSON-ify all of it.
"""

from flask import Flask, jsonify, make_response, request

app = Flask(__name__)

_ROWS = [("1", "bolt", "40"), ("2", "nut", "12")]


@app.route("/export.csv", methods=["GET"])
def export_csv():
    body = "id,name,qty\n" + "\n".join(",".join(row) for row in _ROWS) + "\n"
    response = make_response(body, 200)
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=export.csv"
    return response


@app.route("/ping", methods=["GET"])
def ping():
    response = make_response("pong", 200)
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    response.headers["X-Service"] = "inventory"
    return response


@app.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    if item_id != 1:
        return jsonify({"error": "item not found"}), 404
    return "", 204


@app.route("/items", methods=["POST"])
def create_item():
    data = request.get_json(silent=True) or {}
    if "name" not in data:
        return jsonify({"error": "name is required"}), 400
    response = jsonify({"id": 9, "name": data["name"]})
    response.status_code = 201
    response.headers["Location"] = "/items/9"
    return response
