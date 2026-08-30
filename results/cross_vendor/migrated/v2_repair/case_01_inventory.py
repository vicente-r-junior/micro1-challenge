from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

_ITEMS = {
    1: {"id": 1, "name": "bolt", "qty": 40},
    2: {"id": 2, "name": "nut", "qty": 12},
    3: {"id": 3, "name": "washer", "qty": 7},
}

class Item(BaseModel):
    name: str
    qty: Optional[int] = 0

@app.get("/health")
async def health():
    return JSONResponse(content={"status": "ok", "page_size": 2})

@app.get("/items")
async def list_items(limit: Optional[int] = Query(default=2)):
    items = list(_ITEMS.values())[:limit]
    return JSONResponse(content={"items": items, "count": len(items)})

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    item = _ITEMS.get(item_id)
    if item is None:
        return JSONResponse(content={"error": "item not found"}, status_code=404)
    return JSONResponse(content=item)

@app.post("/items")
async def create_item(data: Item):
    if "name" not in data.dict():
        return JSONResponse(content={"error": "name is required"}, status_code=400)
    if not isinstance(data.name, str):
        return JSONResponse(content={"error": "name must be a string"}, status_code=400)
    qty = data.qty
    new_id = max(_ITEMS) + 1
    return JSONResponse(content={"id": new_id, "name": data.name, "qty": qty}, status_code=201)

@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    if item_id not in _ITEMS:
        return JSONResponse(content={"error": "item not found"}, status_code=404)
    return JSONResponse(content={"deleted": item_id})