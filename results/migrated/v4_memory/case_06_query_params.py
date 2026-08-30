from typing import List, Optional
from fastapi import FastAPI, Query

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

_PRODUCTS = [
    {"id": 1, "name": "bolt", "tag": "hardware", "price": 3},
    {"id": 2, "name": "nut", "tag": "hardware", "price": 1},
    {"id": 3, "name": "manual", "tag": "docs", "price": 0},
]


@app.get("/search")
def search(
    q: str = "",
    limit: Optional[str] = Query(default=None),
    max_price: Optional[str] = Query(default=None),
    include_free: str = "false",
    tag: List[str] = Query(default=[]),
):
    term = q
    limit_value = None
    if limit is not None:
        try:
            limit_value = int(limit)
        except ValueError:
            limit_value = None
    max_price_value = None
    if max_price is not None:
        try:
            max_price_value = float(max_price)
        except ValueError:
            max_price_value = None
    include_free_bool = include_free.lower() in ("1", "true", "yes")
    rows = [p for p in _PRODUCTS if term.lower() in p["name"].lower()]
    if tag:
        rows = [p for p in rows if p["tag"] in tag]
    if max_price_value is not None:
        rows = [p for p in rows if p["price"] <= max_price_value]
    if not include_free_bool:
        rows = [p for p in rows if p["price"] > 0]
    if limit_value:
        rows = rows[:limit_value]
    return {"results": rows, "count": len(rows), "echo": {"q": term, "limit": limit_value}}


@app.get("/facets")
def facets():
    counts = {}
    for product in _PRODUCTS:
        counts[product["tag"]] = counts.get(product["tag"], 0) + 1
    return {"tags": counts}