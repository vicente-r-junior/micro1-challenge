"""Query-string heavy search endpoint. Synthetic case for this benchmark.

Exercises: typed query parameters with defaults, getlist for repeated values,
a truthy-string boolean, and silent coercion failures.
"""

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from typing import List, Optional

app = FastAPI()

_PRODUCTS = [
    {"id": 1, "name": "bolt", "tag": "hardware", "price": 3},
    {"id": 2, "name": "nut", "tag": "hardware", "price": 1},
    {"id": 3, "name": "manual", "tag": "docs", "price": 0},
]

@app.get("/search")
async def search(
    q: str = "",
    limit: Optional[str] = None,
    max_price: Optional[str] = None,
    include_free: str = "false",
    tag: List[str] = Query(default=[])
):
    include_free_bool = include_free.lower() in ("1", "true", "yes")
    
    # Convert limit and max_price to their respective types if they are not None
    limit_value = int(limit) if limit is not None and limit.isdigit() else None
    max_price_value = float(max_price) if max_price is not None and max_price.replace('.', '', 1).isdigit() else None
    
    rows = [p for p in _PRODUCTS if q.lower() in p["name"].lower()]
    if tag:
        rows = [p for p in rows if p["tag"] in tag]
    if max_price_value is not None:
        rows = [p for p in rows if p["price"] <= max_price_value]
    if not include_free_bool:
        rows = [p for p in rows if p["price"] > 0]
    if limit_value is not None:
        rows = rows[:limit_value]
    
    return JSONResponse(content={"results": rows, "count": len(rows), "echo": {"q": q, "limit": limit_value}})

@app.get("/facets")
async def facets():
    counts = {}
    for product in _PRODUCTS:
        counts[product["tag"]] = counts.get(product["tag"], 0) + 1
    return JSONResponse(content={"tags": counts})