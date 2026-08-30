from typing import Any

from fastapi import FastAPI, Query
from pydantic import BaseModel, ConfigDict

app = FastAPI()

_PRODUCTS = [
    {"id": 1, "name": "bolt", "tag": "hardware", "price": 3},
    {"id": 2, "name": "nut", "tag": "hardware", "price": 1},
    {"id": 3, "name": "manual", "tag": "docs", "price": 0},
]


class SearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[dict[str, Any]]
    count: int
    echo: dict[str, Any]


class FacetsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tags: dict[str, int]


@app.get("/search", response_model=SearchResponse)
def search(
    q: str = "",
    limit: int | None = Query(default=None),
    max_price: float | None = Query(default=None),
    include_free: bool = Query(default=False),
    tag: list[str] = Query(default_factory=list),
):
    term = q
    tags = tag

    rows = [p for p in _PRODUCTS if term.lower() in p["name"].lower()]
    if tags:
        rows = [p for p in rows if p["tag"] in tags]
    if max_price is not None:
        rows = [p for p in rows if p["price"] <= max_price]
    if not include_free:
        rows = [p for p in rows if p["price"] > 0]
    if limit:
        rows = rows[:limit]
    return {"results": rows, "count": len(rows), "echo": {"q": term, "limit": limit}}


@app.get("/facets", response_model=FacetsResponse)
def facets():
    counts: dict[str, int] = {}
    for product in _PRODUCTS:
        counts[product["tag"]] = counts.get(product["tag"], 0) + 1
    return {"tags": counts}