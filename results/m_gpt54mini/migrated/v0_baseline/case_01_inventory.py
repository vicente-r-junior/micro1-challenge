"""Small inventory service. Synthetic case, written for this benchmark.

Exercises: JSON body handling, manual validation with explicit 400s, a query
parameter with a default, path converters, and 404 on a missing resource.
"""

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

app = FastAPI()
app.state.page_size = 2

_ITEMS = {
    1: {"id": 1, "name": "bolt", "qty": 40},
    2: {"id": 2, "name": "nut", "qty": 12},
    3: {"id": 3, "name": "washer", "qty": 7},
}


class Item(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    qty: int


class CreateItemRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    qty: int = 0


@app.get("/items")
def list_items(limit: int | None = Query(default=None)):
    effective_limit = limit or app.state.page_size
    items = list(_ITEMS.values())[:effective_limit]
    return {"items": items, "count": len(items)}


@app.get("/items/{item_id}")
def get_item(item_id: int):
    item = _ITEMS.get(item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "item not found"})
    return item


@app.post("/items", status_code=status.HTTP_201_CREATED)
async def create_item(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "body must be JSON"}, status_code=status.HTTP_400_BAD_REQUEST)

    if not data:
        return JSONResponse({"error": "body must be JSON"}, status_code=status.HTTP_400_BAD_REQUEST)

    if "name" not in data:
        return JSONResponse({"error": "name is required"}, status_code=status.HTTP_400_BAD_REQUEST)

    if not isinstance(data["name"], str):
        return JSONResponse({"error": "name must be a string"}, status_code=status.HTTP_400_BAD_REQUEST)

    qty = data.get("qty", 0)
    new_id = max(_ITEMS) + 1
    return {"id": new_id, "name": data["name"], "qty": qty}


@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    if item_id not in _ITEMS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "item not found"})
    return {"deleted": item_id}


@app.get("/health")
def health():
    return {"status": "ok", "page_size": app.state.page_size}