'''Small inventory service. Synthetic case, written for this benchmark.

Exercises: JSON body handling, manual validation with explicit 400s, a query
parameter with a default, path converters, and 404 on a missing resource.
'''

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
import json

app = FastAPI()

PAGE_SIZE = 2

_ITEMS = {
    1: {'id': 1, 'name': 'bolt', 'qty': 40},
    2: {'id': 2, 'name': 'nut', 'qty': 12},
    3: {'id': 3, 'name': 'washer', 'qty': 7},
}


def get_page_size() -> int:
    return PAGE_SIZE


def _json_error(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(content={'error': message}, status_code=status_code)


def _is_json_content_type(content_type) -> bool:
    if content_type is None:
        return False
    mimetype = content_type.split(';', 1)[0].strip().lower()
    return mimetype == 'application/json' or mimetype.endswith('+json')


@app.get('/health')
def health(page_size: int = Depends(get_page_size)):
    return JSONResponse(content={'status': 'ok', 'page_size': page_size})


@app.get('/items')
def list_items(request: Request, page_size: int = Depends(get_page_size)):
    limit = None
    raw_limit = request.query_params.get('limit')
    if raw_limit is not None:
        try:
            limit = int(raw_limit)
        except ValueError:
            limit = None

    if not limit:
        limit = page_size

    items = list(_ITEMS.values())[:limit]
    return JSONResponse(content={'items': items, 'count': len(items)})


@app.get('/items/{item_id}')
def get_item(item_id: int):
    item = _ITEMS.get(item_id)
    if item is None:
        return _json_error('item not found', 404)
    return JSONResponse(content=item)


@app.post('/items')
async def create_item(request: Request):
    data = None
    content_type = request.headers.get('content-type')
    if _is_json_content_type(content_type):
        body = await request.body()
        try:
            data = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = None

    if not data:
        return _json_error('body must be JSON', 400)
    if 'name' not in data:
        return _json_error('name is required', 400)
    if not isinstance(data['name'], str):
        return _json_error('name must be a string', 400)

    qty = data.get('qty', 0)
    new_id = max(_ITEMS) + 1
    return JSONResponse(
        content={'id': new_id, 'name': data['name'], 'qty': qty},
        status_code=201,
    )


@app.delete('/items/{item_id}')
def delete_item(item_id: int):
    if item_id not in _ITEMS:
        return _json_error('item not found', 404)
    return JSONResponse(content={'deleted': item_id})