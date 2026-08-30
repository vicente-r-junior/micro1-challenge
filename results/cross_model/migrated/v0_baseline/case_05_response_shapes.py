from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ValidationError

app = FastAPI()

_ROWS = [("1", "bolt", "40"), ("2", "nut", "12")]

class ItemCreate(BaseModel):
    name: str

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
        return JSONResponse(status_code=404, content={"error": "item not found"})
    return Response(status_code=204)

@app.post("/items")
async def create_item(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    try:
        item = ItemCreate.model_validate(data)
    except ValidationError:
        return JSONResponse(status_code=400, content={"error": "name is required"})
    return JSONResponse(
        status_code=201,
        content={"id": 9, "name": item.name},
        headers={"Location": "/items/9"},
    )