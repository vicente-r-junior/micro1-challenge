"""Query-string heavy search endpoint migrated from Flask to FastAPI."""

from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

_PRODUCTS = [
    {"id": 1, "name": "bolt", "tag": "hardware", "price": 3},
    {"id": 2, "name": "nut", "tag": "hardware", "price": 1},
    {"id": 3, "name": "manual", "tag": "docs", "price": 0},
]


def _coerce_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@app.get("/search")
def search(request: Request):
    query_params = request.query_params

    term = query_params.get("q", "")
    limit = _coerce_int(query_params.get("limit"))
    max_price = _coerce_float(query_params.get("max_price"))
    include_free = query_params.get("include_free", "false").lower() in ("1", "true", "yes")
    tags = query_params.getlist("tag")

    rows = [p for p in _PRODUCTS if term.lower() in p["name"].lower()]
    if tags:
        rows = [p for p in rows if p["tag"] in tags]
    if max_price is not None:
        rows = [p for p in rows if p["price"] <= max_price]
    if not include_free:
        rows = [p for p in rows if p["price"] > 0]
    if limit:
        rows = rows[:limit]

    return JSONResponse(content={"results": rows, "count": len(rows), "echo": {"q": term, "limit": limit}})


@app.get("/facets")
def facets():
    counts = {}
    for product in _PRODUCTS:
        counts[product["tag"]] = counts.get(product["tag"], 0) + 1
    return JSONResponse(content={"tags": counts})