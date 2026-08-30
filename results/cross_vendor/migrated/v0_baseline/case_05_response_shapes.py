from fastapi import FastAPI, Response, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI()

_ROWS = [("1", "bolt", "40"), ("2", "nut", "12")]


@app.get("/export.csv")
async def export_csv():
    body = "id,name,qty\n" + "\n".join(",".join(row) for row in _ROWS) + "\n"
    headers = {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": "attachment; filename=export.csv"
    }
    return Response(content=body, media_type="text/csv", headers=headers)


@app.get("/ping")
async def ping():
    headers = {
        "Content-Type": "text/plain; charset=utf-8",
        "X-Service": "inventory"
    }
    return Response(content="pong", media_type="text/plain", headers=headers)


@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    if item_id != 1:
        raise HTTPException(status_code=404, detail={"error": "item not found"})
    return Response(status_code=204)


class Item(BaseModel):
    name: str


@app.post("/items")
async def create_item(item: Item):
    response = {
        "id": 9,
        "name": item.name
    }
    headers = {
        "Location": "/items/9"
    }
    return Response(content=response, status_code=201, headers=headers)