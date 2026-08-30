from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

_PRODUCTS = [
    {"id": 1, "name": "bolt", "tag": "hardware", "price": 3},
    {"id": 2, "name": "nut", "tag": "hardware", "price": 1},
    {"id": 3, "name": "manual", "tag": "docs", "price": 0},
]

class SearchResponse(BaseModel):
    results: List[dict]
    count: int
    echo: dict

@app.get("/search", response_model=SearchResponse)
async def search(
    q: str = "",
    limit: Optional[int] = None,
    max_price: Optional[float] = None,
    include_free: bool = Query(False, alias="include_free"),
    tag: List[str] = Query([])
):
    rows = [p for p in _PRODUCTS if q.lower() in p["name"].lower()]
    if tag:
        rows = [p for p in rows if p["tag"] in tag]
    if max_price is not None:
        rows = [p for p in rows if p["price"] <= max_price]
    if not include_free:
        rows = [p for p in rows if p["price"] > 0]
    if limit:
        rows = rows[:limit]
    return JSONResponse(content={"results": rows, "count": len(rows), "echo": {"q": q, "limit": limit}})

class FacetsResponse(BaseModel):
    tags: dict

@app.get("/facets", response_model=FacetsResponse)
async def facets():
    counts = {}
    for product in _PRODUCTS:
        counts[product["tag"]] = counts.get(product["tag"], 0) + 1
    return JSONResponse(content={"tags": counts})