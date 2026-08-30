from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

_ITEMS = {
    1: {"id": 1, "name": "bolt", "qty": 40},
    2: {"id": 2, "name": "nut", "qty": 12},
    3: {"id": 3, "name": "washer", "qty": 7},
}

class Item(BaseModel):
    id: int
    name: str
    qty: int

class ItemCreate(BaseModel):
    name: str
    qty: Optional[int] = 0

@app.get("/items", response_model=dict[str, List[Item]])
async def list_items(limit: int = Query(2)):
    items = list(_ITEMS.values())[:limit]
    return {"items": items, "count": len(items)}

@app.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    item = _ITEMS.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return item

@app.post("/items", response_model=Item, status_code=201)
async def create_item(item: ItemCreate):
    new_id = max(_ITEMS) + 1
    new_item = {"id": new_id, "name": item.name, "qty": item.qty}
    _ITEMS[new_id] = new_item
    return new_item

@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    if item_id not in _ITEMS:
        raise HTTPException(status_code=404, detail="item not found")
    del _ITEMS[item_id]
    return {"deleted": item_id}

@app.get("/health")
async def health():
    return {"status": "ok", "page_size": 2}