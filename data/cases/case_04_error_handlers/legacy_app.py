"""Centralised error handling. Synthetic case for this benchmark.

Exercises: @app.errorhandler for a custom exception and for 404/405, abort()
with a description, and a uniform error envelope every client parses.
"""

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

_ACCOUNTS = {"a1": {"id": "a1", "balance": 100}}


class InsufficientFunds(Exception):
    def __init__(self, needed, available):
        super().__init__("insufficient funds")
        self.needed = needed
        self.available = available


@app.errorhandler(InsufficientFunds)
def on_insufficient_funds(exc):
    return jsonify({"error": "insufficient_funds", "needed": exc.needed, "available": exc.available}), 409


@app.errorhandler(HTTPException)
def on_http_error(exc):
    return jsonify({"error": "http_error", "status": exc.code, "message": exc.name}), exc.code


@app.route("/accounts/<account_id>", methods=["GET"])
def get_account(account_id):
    account = _ACCOUNTS.get(account_id)
    if account is None:
        return jsonify({"error": "not_found", "resource": "account"}), 404
    return jsonify(account)


@app.route("/accounts/<account_id>/withdraw", methods=["POST"])
def withdraw(account_id):
    account = _ACCOUNTS.get(account_id)
    if account is None:
        return jsonify({"error": "not_found", "resource": "account"}), 404
    data = request.get_json(silent=True) or {}
    amount = data.get("amount")
    if not isinstance(amount, int) or amount <= 0:
        return jsonify({"error": "bad_amount"}), 400
    if amount > account["balance"]:
        raise InsufficientFunds(amount, account["balance"])
    return jsonify({"id": account_id, "withdrawn": amount, "balance": account["balance"] - amount})
