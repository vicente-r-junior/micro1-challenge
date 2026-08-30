from fastapi import FastAPI, Query

app = FastAPI()

_PRODUCTS = [
    {"id": 1, "name": "bolt", "price": 3, "tag": "hardware"},
    {"id": 2, "name": "nut", "price": 1, "tag": "hardware"},
    {"id": 3, "name": "manual", "price": 0, "tag": "docs"},
]


@app.get("/search")
def search(
    q: str = Query(default=""),
    limit: str = Query(default=None),
    max_price: str = Query(default=None),
    include_free: str = Query(default="false"),
    tags: list[str] = Query(default=None, alias="tag"),
):
    term = q
    if tags is None:
        tags = []

    if limit is None:
        real_limit = None
    else:
        try:
            real_limit = int(limit)
        except ValueError:
            real_limit = None

    if max_price is None:
        real_max_price = None
    else:
        try:
            real_max_price = float(max_price)
        except ValueError:
            real_max_price = None

    include_free = include_free.lower() in ("1", "true", "yes")

    rows = [p for p in _PRODUCTS if term.lower() in p["name"].lower()]
    if tags:
        rows = [p for p in rows if p["tag"] in tags]
    if real_max_price is not None:
        rows = [p for p in rows if p["price"] <= real_max_price]
    if not include_free:
        rows = [p for p in rows if p["price"] > 0]
    if real_limit:
        rows = rows[:real_limit]

    return {
        "count": len(rows),
        "echo": {"limit": real_limit, "q": term},
        "results": rows,
    }


@app.get("/facets")
def facets():
    counts = {}
    for product in _PRODUCTS:
        counts[product["tag"]] = counts.get(product["tag"], 0) + 1
    return {"tags": dict(sorted(counts.items()))}