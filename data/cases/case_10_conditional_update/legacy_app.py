"""Optimistic concurrency with a version header. Synthetic case.

Exercises: a request header that drives control flow, PATCH semantics, 409 on a
version mismatch, 428 when the header is absent, and a response header echoing
the new version.
"""

from flask import Flask, jsonify, make_response, request

app = Flask(__name__)

_DOCS = {"d1": {"id": "d1", "title": "spec", "version": 3}}


@app.route("/docs/<doc_id>", methods=["GET"])
def get_doc(doc_id):
    doc = _DOCS.get(doc_id)
    if doc is None:
        return jsonify({"error": "doc not found"}), 404
    response = make_response(jsonify(doc), 200)
    response.headers["ETag"] = f'W/"{doc["version"]}"'
    return response


@app.route("/docs/<doc_id>", methods=["PATCH"])
def patch_doc(doc_id):
    doc = _DOCS.get(doc_id)
    if doc is None:
        return jsonify({"error": "doc not found"}), 404

    if_match = request.headers.get("If-Match")
    if not if_match:
        return jsonify({"error": "If-Match header is required", "code": "PRECONDITION_REQUIRED"}), 428
    if if_match != f'W/"{doc["version"]}"':
        return jsonify({"error": "version conflict", "expected": doc["version"]}), 409

    data = request.get_json(silent=True) or {}
    title = data.get("title")
    if not isinstance(title, str) or not title:
        return jsonify({"error": "title must be a non-empty string"}), 400

    response = make_response(jsonify({**doc, "title": title, "version": doc["version"] + 1}), 200)
    response.headers["ETag"] = f'W/"{doc["version"] + 1}"'
    return response
