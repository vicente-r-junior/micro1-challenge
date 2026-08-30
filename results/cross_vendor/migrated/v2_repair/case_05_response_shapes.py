from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

_ROWS = [("1", "bolt", "40"), ("2", "nut", "12")]

class ItemCreate(BaseModel):
    name: str

@app.get("/export.csv")
def export_csv():
    body = "id,name,qty\n" + "\n".join(",".join(row) for row in _ROWS) + "\n"
    response = Response(content=body, media_type="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = "attachment; filename=export.csv"
    return response

@app.get("/ping")
def ping():
    response = Response(content="pong", media_type="text/plain; charset=utf-8")
    response.headers["X-Service"] = "inventory"
    return response

@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    if item_id != 1:
        return JSONResponse(content={"error": "item not found"}, status_code=404)
    return Response(status_code=204)

@app.post("/items")
def create_item(item: ItemCreate):
    response = JSONResponse(content={"id": 9, "name": item.name}, status_code=201)
    response.headers["Location"] = "/items/9"
    return response