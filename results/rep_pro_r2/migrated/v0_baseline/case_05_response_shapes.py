from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

_ROWS = [("1", "bolt", "40"), ("2", "nut", "12")]

app = FastAPI()


class ItemResponse(BaseModel):
    id: int
    name: Any


class ErrorResponse(BaseModel):
    error: str


@app.get("/export.csv")
def export_csv():
    body = "id,name,qty\n" + "\n".join(",".join(row) for row in _ROWS) + "\n"
    return Response(
        content=body,
        headers={
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": "attachment; filename=export.csv",
        },
    )


@app.get("/ping")
def ping():
    return Response(
        content="pong",
        headers={
            "Content-Type": "text/plain; charset=utf-8",
            "X-Service": "inventory",
        },
    )


@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    if item_id != 1:
        return JSONResponse(
            ErrorResponse(error="item not found").model_dump(),
            status_code=404,
        )
    return Response(status_code=204)


@app.post("/items", response_model=ItemResponse, status_code=201)
async def create_item(request: Request, response: Response):
    try:
        data = await request.json()
    except Exception:
        data = {}

    if not isinstance(data, dict) or "name" not in data:
        return JSONResponse(
            ErrorResponse(error="name is required").model_dump(),
            status_code=400,
        )

    response.headers["Location"] = "/items/9"
    return ItemResponse(id=9, name=data["name"])