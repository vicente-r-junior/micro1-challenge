'''Query-string heavy search endpoint. Synthetic case for this benchmark.

Exercises: typed query parameters with defaults, getlist for repeated values,
a truthy-string boolean, and silent coercion failures.
'''

from typing import Dict, List, Optional

from fastapi import FastAPI, Query
from pydantic import BaseModel

app = FastAPI()

_PRODUCTS = [
    {'id': 1, 'name': 'bolt', 'tag': 'hardware', 'price': 3},
    {'id': 2, 'name': 'nut', 'tag': 'hardware', 'price': 1},
    {'id': 3, 'name': 'manual', 'tag': 'docs', 'price': 0},
]


class Product(BaseModel):
    id: int
    name: str
    tag: str
    price: int


class SearchEcho(BaseModel):
    q: str
    limit: Optional[int] = None


class SearchResponse(BaseModel):
    results: List[Product]
    count: int
    echo: SearchEcho


class FacetsResponse(BaseModel):
    tags: Dict[str, int]


def _try_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _try_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@app.get('/search', response_model=SearchResponse)
def search(
    q: str = Query(''),
    limit: Optional[str] = Query(None),
    max_price: Optional[str] = Query(None),
    include_free: str = Query('false'),
    tags: Optional[List[str]] = Query(None),
):
    term = q
    limit_int = _try_int(limit)
    max_price_float = _try_float(max_price)
    include_free_bool = include_free.lower() in ('1', 'true', 'yes')
    tag_list = tags or []

    rows = [p for p in _PRODUCTS if term.lower() in p['name'].lower()]
    if tag_list:
        rows = [p for p in rows if p['tag'] in tag_list]
    if max_price_float is not None:
        rows = [p for p in rows if p['price'] <= max_price_float]
    if not include_free_bool:
        rows = [p for p in rows if p['price'] > 0]
    if limit_int:
        rows = rows[:limit_int]

    return {'results': rows, 'count': len(rows), 'echo': {'q': term, 'limit': limit_int}}


@app.get('/facets', response_model=FacetsResponse)
def facets():
    counts = {}
    for product in _PRODUCTS:
        counts[product['tag']] = counts.get(product['tag'], 0) + 1
    return {'tags': counts}