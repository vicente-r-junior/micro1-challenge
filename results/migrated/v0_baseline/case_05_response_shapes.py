# Responses that are not plain JSON. Synthetic case for this benchmark.
# FastAPI migration.

from typing import Optional

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

_ROWS = [("1", "bolt", "40"), ("2", "nut", "12")]


class ItemCreate(BaseModel):
    name: Optional[str] = None


@app.get("/export.csv")
def export_csv():
    body = "id,name,qty\n" + "\n".join(",".join(row) for row in _ROWS) + "\n"
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=export.csv"},
    )


@app.get("/ping")
def ping():
    return Response(
        content="pong",
        media_type="text/plain; charset=utf-8",
        headers={"X-Service": "inventory"},
    )


@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    if item_id != 1:
        return JSONResponse({"error": "item not found"}, status_code=404)
    return Response(status_code=204)


@app.post("/items")
def create_item(item: ItemCreate):
    if "name" not in item.model_fields_set:
        return JSONResponse({"error": "name is required"}, status_code=400)
    return JSONResponse(
        content={"id": 9, "name": item.name},
        status_code=201,
        headers={"Location": "/items/9"},
    )