"""Small inventory service. Migrated from Flask to FastAPI.

Exercises: JSON body handling, manual validation with explicit 400s, a query
parameter with a default, path converters, and 404 on a missing resource.
"""

from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

import json

app = FastAPI()

PAGE_SIZE = 2

_ITEMS = {
    1: {"id": 1, "name": "bolt", "qty": 40},
    2: {"id": 2, "name": "nut", "qty": 12},
    3: {"id": 3, "name": "washer", "qty": 7},
}


class Item(BaseModel):
    id: int
    name: str
    qty: Any


class ItemCreate(BaseModel):
    name: str
    qty: Any = 0


@app.get("/items")
def list_items(limit: Optional[str] = None):
    if limit is None:
        resolved_limit = PAGE_SIZE
    else:
        try:
            resolved_limit = int(limit)
        except ValueError:
            resolved_limit = PAGE_SIZE
        if not resolved_limit:
            resolved_limit = PAGE_SIZE
    items = list(_ITEMS.values())[:resolved_limit]
    return {"items": items, "count": len(items)}


@app.get("/items/{item_id}")
def get_item(item_id: int):
    item = _ITEMS.get(item_id)
    if item is None:
        return JSONResponse(status_code=404, content={"error": "item not found"})
    return JSONResponse(status_code=200, content=item)


@app.post("/items")
async def create_item(request: Request):
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        return JSONResponse(status_code=400, content={"error": "body must be JSON"})

    if not payload:
        return JSONResponse(status_code=400, content={"error": "body must be JSON"})

    if not isinstance(payload, dict):
        return JSONResponse(status_code=400, content={"error": "name is required"})

    try:
        item_data = ItemCreate.model_validate(payload)
    except ValidationError as exc:
        for err in exc.errors():
            if err["loc"] == ("name",) and err["type"] == "missing":
                return JSONResponse(status_code=400, content={"error": "name is required"})
            if err["loc"] == ("name",) and err["type"] == "string_type":
                return JSONResponse(status_code=400, content={"error": "name must be a string"})
        return JSONResponse(status_code=400, content={"error": "invalid payload"})

    new_id = max(_ITEMS) + 1
    return JSONResponse(
        status_code=201,
        content={"id": new_id, "name": item_data.name, "qty": item_data.qty},
    )


@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    if item_id not in _ITEMS:
        return JSONResponse(status_code=404, content={"error": "item not found"})
    return {"deleted": item_id}


@app.get("/health")
def health():
    return {"status": "ok", "page_size": PAGE_SIZE}