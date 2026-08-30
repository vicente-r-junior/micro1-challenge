"""Token-guarded blueprint. Synthetic case, written for this benchmark.

Exercises: Blueprint with url_prefix, before_request guard, flask.g, 401 with a
custom body, and a header-driven code path. A migration that turns the guard
into a FastAPI dependency usually changes the 401 payload shape.
"""

from flask import Blueprint, Flask, abort, g, jsonify, request

api = Blueprint("api", __name__, url_prefix="/api/v1")

_TOKENS = {"secret-token": {"user": "ana", "role": "admin"}}
_NOTES = {1: {"id": 1, "owner": "ana", "text": "first"}}


@api.before_request
def authenticate():
    token = request.headers.get("X-Api-Token")
    if not token:
        return jsonify({"error": "missing token", "code": "AUTH_001"}), 401
    identity = _TOKENS.get(token)
    if identity is None:
        return jsonify({"error": "invalid token", "code": "AUTH_002"}), 401
    g.identity = identity


@api.route("/whoami", methods=["GET"])
def whoami():
    return jsonify({"user": g.identity["user"], "role": g.identity["role"]})


@api.route("/notes/<int:note_id>", methods=["GET"])
def get_note(note_id):
    note = _NOTES.get(note_id)
    if note is None:
        abort(404)
    if note["owner"] != g.identity["user"]:
        return jsonify({"error": "forbidden"}), 403
    return jsonify(note)


@api.route("/notes", methods=["POST"])
def create_note():
    data = request.get_json(silent=True) or {}
    text = data.get("text")
    if not text:
        return jsonify({"error": "text is required", "code": "VAL_001"}), 422
    return jsonify({"id": 2, "owner": g.identity["user"], "text": text}), 201


app = Flask(__name__)
app.register_blueprint(api)
