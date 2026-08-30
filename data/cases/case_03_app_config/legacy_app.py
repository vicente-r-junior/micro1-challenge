"""Configuration read through current_app. Synthetic case for this benchmark.

Exercises: current_app.config lookups inside handlers, a config-derived default,
and a feature flag that changes the response shape. The migration has to turn
this into dependency injection without changing what clients see.
"""

from flask import Flask, current_app, jsonify, request

app = Flask(__name__)
app.config.update(
    PAGE_SIZE=3,
    FEATURE_VERBOSE=True,
    SERVICE_NAME="reporting",
    MAX_RANGE_DAYS=30,
)

_ROWS = [{"id": i, "value": i * 10} for i in range(1, 11)]


@app.route("/config", methods=["GET"])
def show_config():
    return jsonify(
        {
            "service": current_app.config["SERVICE_NAME"],
            "page_size": current_app.config["PAGE_SIZE"],
            "verbose": current_app.config["FEATURE_VERBOSE"],
        }
    )


@app.route("/rows", methods=["GET"])
def rows():
    size = request.args.get("size", type=int) or current_app.config["PAGE_SIZE"]
    page = _ROWS[:size]
    payload = {"rows": page}
    if current_app.config["FEATURE_VERBOSE"]:
        payload["meta"] = {"returned": len(page), "total": len(_ROWS)}
    return jsonify(payload)


@app.route("/report", methods=["POST"])
def report():
    data = request.get_json(silent=True) or {}
    days = data.get("days", 7)
    if not isinstance(days, int):
        return jsonify({"error": "days must be an integer"}), 400
    if days > current_app.config["MAX_RANGE_DAYS"]:
        return jsonify({"error": "range too large", "max": current_app.config["MAX_RANGE_DAYS"]}), 400
    return jsonify({"service": current_app.config["SERVICE_NAME"], "days": days}), 202
