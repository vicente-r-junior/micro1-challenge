"""Query-string heavy search endpoint migrated from Flask to FastAPI.

Preserves Flask-style query behavior for this endpoint, including first-value
lookup for repeated scalar query parameters, getlist-style repeated values,
truthy-string booleans, and silent coercion failures.
"""

from typing import Callable, Optional, TypeVar
from urllib.parse import parse_qsl

from fastapi import FastAPI, Request
from pydantic import BaseModel

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


class SearchEcho(BaseModel):
    q: str
    limit: Optional[int]


class SearchResponse(BaseModel):
    results: list[Product]
    count: int
    echo: SearchEcho


class FacetsResponse(BaseModel):
    tags: dict[str, int]


T = TypeVar("T")


def _query_pairs(request: Request) -> list[tuple[str, str]]:
    raw_query_string = request.scope.get("query_string", b"")
    query_string = raw_query_string.decode("latin-1")
    return parse_qsl(
        query_string,
        keep_blank_values=True,
        encoding="utf-8",
        errors="replace",
    )


def _first_arg(
    pairs: list[tuple[str, str]],
    name: str,
    default: Optional[str] = None,
) -> Optional[str]:
    for key, value in pairs:
        if key == name:
            return value
    return default


def _arg_list(pairs: list[tuple[str, str]], name: str) -> list[str]:
    return [value for key, value in pairs if key == name]


def _silent_coerce(value: Optional[str], converter: Callable[[str], T]) -> Optional[T]:
    if value is None:
        return None
    try:
        return converter(value)
    except (TypeError, ValueError):
        return None


@app.get("/search")
def search(request: Request) -> dict:
    pairs = _query_pairs(request)

    term = _first_arg(pairs, "q", "") or ""
    limit = _silent_coerce(_first_arg(pairs, "limit"), int)
    max_price = _silent_coerce(_first_arg(pairs, "max_price"), float)
    include_free_value = _first_arg(pairs, "include_free", "false") or ""
    include_free = include_free_value.lower() in ("1", "true", "yes")
    tags = _arg_list(pairs, "tag")

    rows = [p for p in _PRODUCTS if term.lower() in p["name"].lower()]
    if tags:
        rows = [p for p in rows if p["tag"] in tags]
    if max_price is not None:
        rows = [p for p in rows if p["price"] <= max_price]
    if not include_free:
        rows = [p for p in rows if p["price"] > 0]
    if limit:
        rows = rows[:limit]

    response = SearchResponse(
        results=rows,
        count=len(rows),
        echo=SearchEcho(q=term, limit=limit),
    )
    return response.model_dump()


@app.get("/facets")
def facets() -> dict:
    counts: dict[str, int] = {}
    for product in _PRODUCTS:
        counts[product["tag"]] = counts.get(product["tag"], 0) + 1

    response = FacetsResponse(tags=counts)
    return response.model_dump()