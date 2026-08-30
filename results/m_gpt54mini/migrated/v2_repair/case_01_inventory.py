from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from typing import Any

app = FastAPI()
app.state.page_size = 2

_ITEMS = {
    1: {"id": 1, "name": "bolt", "qty": 40},
    2: {"id": 2, "name": "nut", "qty": 12},
    3: {"id": 3, "name": "washer", "qty": 7},
}


def _json_response(content: Any, status_code: int = 200):
    return JSONResponse(content=content, status_code=status_code)


@app.get("/items")
async def list_items(request: Request):
    limit_raw = request.query_params.get("limit")
    limit = None
    if limit_raw is not None:
        try:
            limit = int(limit_raw)
        except (TypeError, ValueError):
            limit = None
    if not limit:
        limit = app.state.page_size
    items = list(_ITEMS.values())[:limit]
    return _json_response({"items": items, "count": len(items)})


@app.get("/items/{item_id}")
async def get_item(item_id: int):
    item = _ITEMS.get(item_id)
    if item is None:
        return _json_response({"error": "item not found"}, status_code=404)
    return _json_response(item)


@app.post("/items")
async def create_item(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = None
    if not data:
        return _json_response({"error": "body must be JSON"}, status_code=400)
    if "name" not in data:
        return _json_response({"error": "name is required"}, status_code=400)
    if not isinstance(data["name"], str):
        return _json_response({"error": "name must be a string"}, status_code=400)
    qty = data.get("qty", 0)
    new_id = max(_ITEMS) + 1
    return _json_response({"id": new_id, "name": data["name"], "qty": qty}, status_code=201)


@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    if item_id not in _ITEMS:
        return _json_response({"error": "item not found"}, status_code=404)
    return _json_response({"deleted": item_id})


@app.get("/health")
async def health():
    return _json_response({"status": "ok", "page_size": app.state.page_size})