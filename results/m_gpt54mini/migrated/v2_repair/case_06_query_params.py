from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

_PRODUCTS = [
    {"id": 1, "name": "bolt", "tag": "hardware", "price": 3},
    {"id": 2, "name": "nut", "tag": "hardware", "price": 1},
    {"id": 3, "name": "manual", "tag": "docs", "price": 0},
]


@app.get("/search")
async def search(request: Request):
    args = request.query_params
    term = args.get("q", "")

    limit_raw = args.get("limit")
    try:
        limit = int(limit_raw) if limit_raw is not None else None
    except (TypeError, ValueError):
        limit = None

    max_price_raw = args.get("max_price")
    try:
        max_price = float(max_price_raw) if max_price_raw is not None else None
    except (TypeError, ValueError):
        max_price = None

    include_free = args.get("include_free", "false").lower() in ("1", "true", "yes")
    tags = request.query_params.getlist("tag")

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
async def facets():
    counts = {}
    for product in _PRODUCTS:
        counts[product["tag"]] = counts.get(product["tag"], 0) + 1
    return JSONResponse(content={"tags": counts})