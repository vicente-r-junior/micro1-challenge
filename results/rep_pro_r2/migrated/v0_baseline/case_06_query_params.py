from typing import Annotated, List, Optional

from fastapi import FastAPI, Query
from pydantic import BeforeValidator

app = FastAPI()

_PRODUCTS = [
    {"id": 1, "name": "bolt", "tag": "hardware", "price": 3},
    {"id": 2, "name": "nut", "tag": "hardware", "price": 1},
    {"id": 3, "name": "manual", "tag": "docs", "price": 0},
]


def _silent_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _silent_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _truthy_bool(value):
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("1", "true", "yes")


@app.get("/search")
def search(
    q: str = "",
    limit: Annotated[Optional[int], Query(), BeforeValidator(_silent_int)] = None,
    max_price: Annotated[Optional[float], Query(), BeforeValidator(_silent_float)] = None,
    include_free: Annotated[bool, Query(), BeforeValidator(_truthy_bool)] = False,
    tags: Annotated[Optional[List[str]], Query(alias="tag")] = None,
):
    tags = tags or []
    rows = [p for p in _PRODUCTS if q.lower() in p["name"].lower()]
    if tags:
        rows = [p for p in rows if p["tag"] in tags]
    if max_price is not None:
        rows = [p for p in rows if p["price"] <= max_price]
    if not include_free:
        rows = [p for p in rows if p["price"] > 0]
    if limit:
        rows = rows[:limit]
    return {"results": rows, "count": len(rows), "echo": {"q": q, "limit": limit}}


@app.get("/facets")
def facets():
    counts = {}
    for product in _PRODUCTS:
        counts[product["tag"]] = counts.get(product["tag"], 0) + 1
    return {"tags": counts}