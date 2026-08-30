# Migrated FastAPI application preserving legacy Flask behavior.

import json

from fastapi import FastAPI, Request
from fastapi.responses import Response
from pydantic import BaseModel  # Pydantic v2 (unused)

app = FastAPI()

_PRODUCTS = [
    {'id': 1, 'name': 'bolt', 'tag': 'hardware', 'price': 3},
    {'id': 2, 'name': 'nut', 'tag': 'hardware', 'price': 1},
    {'id': 3, 'name': 'manual', 'tag': 'docs', 'price': 0},
]


def _parse_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _parse_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _json_response(content, status_code=200):
    body = json.dumps(content, sort_keys=True) + '\n'
    return Response(
        content=body,
        status_code=status_code,
        headers={'content-type': 'application/json'},
    )


@app.get('/search')
def search(request: Request):
    params = request.query_params
    term = params.get('q', '')
    limit = _parse_int(params.get('limit'))
    max_price = _parse_float(params.get('max_price'))
    include_free = params.get('include_free', 'false').lower() in ('1', 'true', 'yes')
    tags = params.getlist('tag')

    rows = [p for p in _PRODUCTS if term.lower() in p['name'].lower()]
    if tags:
        rows = [p for p in rows if p['tag'] in tags]
    if max_price is not None:
        rows = [p for p in rows if p['price'] <= max_price]
    if not include_free:
        rows = [p for p in rows if p['price'] > 0]
    if limit:
        rows = rows[:limit]
    return _json_response({'results': rows, 'count': len(rows), 'echo': {'q': term, 'limit': limit}})


@app.get('/facets')
def facets():
    counts = {}
    for product in _PRODUCTS:
        counts[product['tag']] = counts.get(product['tag'], 0) + 1
    return _json_response({'tags': counts})