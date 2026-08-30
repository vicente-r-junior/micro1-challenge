from typing import Any, List, Optional

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()
PAGE_SIZE = 2

_ITEMS = {
    1: {'id': 1, 'name': 'bolt', 'qty': 40},
    2: {'id': 2, 'name': 'nut', 'qty': 12},
    3: {'id': 3, 'name': 'washer', 'qty': 7},
}


class Item(BaseModel):
    id: int
    name: str
    qty: Any


class ItemList(BaseModel):
    items: List[Item]
    count: int


@app.get('/items', response_model=ItemList)
def list_items(limit: Optional[int] = Query(default=None)):
    effective_limit = limit or PAGE_SIZE
    items = list(_ITEMS.values())[:effective_limit]
    return {'items': items, 'count': len(items)}


@app.get('/items/{item_id}')
def get_item(item_id: int):
    item = _ITEMS.get(item_id)
    if item is None:
        return JSONResponse(status_code=404, content={'error': 'item not found'})
    return item


@app.post('/items', status_code=201)
async def create_item(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={'error': 'body must be JSON'})

    if not data:
        return JSONResponse(status_code=400, content={'error': 'body must be JSON'})
    if 'name' not in data:
        return JSONResponse(status_code=400, content={'error': 'name is required'})
    if not isinstance(data['name'], str):
        return JSONResponse(status_code=400, content={'error': 'name must be a string'})

    qty = data.get('qty', 0)
    new_id = max(_ITEMS) + 1
    return {'id': new_id, 'name': data['name'], 'qty': qty}


@app.delete('/items/{item_id}')
def delete_item(item_id: int):
    if item_id not in _ITEMS:
        return JSONResponse(status_code=404, content={'error': 'item not found'})
    return {'deleted': item_id}


@app.get('/health')
def health():
    return {'status': 'ok', 'page_size': PAGE_SIZE}