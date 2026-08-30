"""Pagination advertised through response headers. Synthetic case.

Exercises: RFC 5988 Link headers, X-Total-Count, an out-of-range page that
returns an empty list with 200 rather than 404, and a cap on page size.
"""

from flask import Flask, jsonify, make_response, request

app = Flask(__name__)

_EVENTS = [{"id": i, "kind": "click"} for i in range(1, 26)]
MAX_PER_PAGE = 10


@app.route("/events", methods=["GET"])
def events():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 5, type=int)

    if page < 1:
        return jsonify({"error": "page must be >= 1"}), 400
    if per_page > MAX_PER_PAGE:
        per_page = MAX_PER_PAGE

    start = (page - 1) * per_page
    rows = _EVENTS[start : start + per_page]
    total = len(_EVENTS)
    last_page = (total + per_page - 1) // per_page

    response = make_response(jsonify({"events": rows, "page": page, "per_page": per_page}), 200)
    response.headers["X-Total-Count"] = str(total)
    links = [f'</events?page=1&per_page={per_page}>; rel="first"',
             f'</events?page={last_page}&per_page={per_page}>; rel="last"']
    if page < last_page:
        links.append(f'</events?page={page + 1}&per_page={per_page}>; rel="next"')
    response.headers["Link"] = ", ".join(links)
    return response
