"""Query-string heavy search endpoint. Synthetic case for this benchmark.

Exercises: typed query parameters with defaults, getlist for repeated values,
a truthy-string boolean, and silent coercion failures.
"""

from typing import Dict, List, Optional

from fastapi import FastAPI, Query
from pydantic import BaseModel
import uvicorn

app = FastAPI()

_PRODUCTS = [
    {"id": 1, "name": "bolt", "tag": "hardware", "price": 3},
    {"id": 2, "name": "nut", "tag": "hardware", "price": 1},
    {"id": 3, "name": "manual", "tag": "docs", "price": 0},
]


class Product(BaseModel):
    id: int
    name: str
    tag: str
    price: int


class Echo(BaseModel):
    q: str
    limit: Optional[int]


class SearchResponse(BaseModel):
    results: List[Product]
    count: int
    echo: Echo


class FacetsResponse(BaseModel):
    tags: Dict[str, int]


def _parse_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


@app.get("/search", response_model=SearchResponse)
def search(
    q: str = "",
    limit: Optional[str] = Query(default=None),
    max_price: Optional[str] = Query(default=None),
    include_free: str = "false",
    tag: List[str] = Query(default=[]),
):
    term = q
    limit_value = _parse_int(limit)
    max_price_value = _parse_float(max_price)
    include_free_value = include_free.lower() in ("1", "true", "yes")
    tags = tag

    rows = [p for p in _PRODUCTS if term.lower() in p["name"].lower()]
    if tags:
        rows = [p for p in rows if p["tag"] in tags]
    if max_price_value is not None:
        rows = [p for p in rows if p["price"] <= max_price_value]
    if not include_free_value:
        rows = [p for p in rows if p["price"] > 0]
    if limit_value:
        rows = rows[:limit_value]

    return {
        "results": rows,
        "count": len(rows),
        "echo": {"q": term, "limit": limit_value},
    }


@app.get("/facets", response_model=FacetsResponse)
def facets():
    counts = {}
    for product in _PRODUCTS:
        counts[product["tag"]] = counts.get(product["tag"], 0) + 1
    return {"tags": counts}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)