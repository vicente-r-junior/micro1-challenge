from typing import Optional

from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel

app = FastAPI()

_PRODUCTS = [
    {"id": 1, "name": "bolt", "tag": "hardware", "price": 3},
    {"id": 2, "name": "nut", "tag": "hardware", "price": 1},
    {"id": 3, "name": "manual", "tag": "docs", "price": 0},
]


class SearchParams(BaseModel):
    q: str = ""
    limit: Optional[int] = None
    max_price: Optional[float] = None
    include_free: bool = False
    tags: list[str] = []


def parse_search_params(request: Request) -> SearchParams:
    query = request.query_params
    q = query.get("q", "")

    limit = query.get("limit")
    if limit is not None:
        try:
            limit = int(limit)
        except ValueError:
            limit = None

    max_price = query.get("max_price")
    if max_price is not None:
        try:
            max_price = float(max_price)
        except ValueError:
            max_price = None

    include_free = query.get("include_free", "false").lower() in ("1", "true", "yes")
    tags = query.getlist("tag")

    return SearchParams(
        q=q,
        limit=limit,
        max_price=max_price,
        include_free=include_free,
        tags=tags,
    )


@app.get("/search")
def search(params: SearchParams = Depends(parse_search_params)):
    term = params.q
    limit = params.limit
    max_price = params.max_price
    include_free = params.include_free
    tags = params.tags

    rows = [p for p in _PRODUCTS if term.lower() in p["name"].lower()]

    if tags:
        rows = [p for p in rows if p["tag"] in tags]
    if max_price is not None:
        rows = [p for p in rows if p["price"] <= max_price]
    if not include_free:
        rows = [p for p in rows if p["price"] > 0]
    if limit:
        rows = rows[:limit]

    return {
        "results": rows,
        "count": len(rows),
        "echo": {"q": term, "limit": limit},
    }


@app.get("/facets")
def facets():
    counts = {}
    for product in _PRODUCTS:
        counts[product["tag"]] = counts.get(product["tag"], 0) + 1
    return {"tags": counts}