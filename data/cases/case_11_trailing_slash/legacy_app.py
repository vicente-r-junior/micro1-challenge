"""Trailing-slash and redirect behaviour. Synthetic case for this benchmark.

Exercises: Flask's strict_slashes redirect, an explicitly non-strict route, and
a route that only exists with the slash. Clients follow these redirects today.
"""

from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/reports/", methods=["GET"])
def list_reports():
    # Declared WITH a trailing slash: Flask answers /reports with a 308 redirect.
    return jsonify({"reports": ["daily", "weekly"]})


@app.route("/status", methods=["GET"])
def status():
    # Declared WITHOUT a trailing slash: Flask answers /status/ with 404.
    return jsonify({"status": "up"})


@app.route("/jobs", methods=["GET"], strict_slashes=False)
def jobs():
    return jsonify({"jobs": []})


@app.route("/queue/<name>", methods=["GET"])
def queue(name):
    return jsonify({"queue": name, "depth": 0})
