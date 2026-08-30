"""FastAPI migration of the Flask application.

Responses intentionally include non-JSON bodies, custom headers, a 204 with no
content, and a JSON creation response with Location header.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

app = FastAPI()

_ROWS = [("1", "bolt", "40"), ("2", "nut", "12")]


class ErrorResponse(BaseModel):
    error: str


class ItemResponse(BaseModel):
    id: int
    name: Any


@app.get("/export.csv")
def export_csv() -> Response:
    body = "id,name,qty\n" + "\n".join(",".join(row) for row in _ROWS) + "\n"
    return Response(
        content=body,
        status_code=200,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=export.csv"},
    )


@app.get("/ping")
def ping() -> Response:
    return Response(
        content="pong",
        status_code=200,
        media_type="text/plain",
        headers={"X-Service": "inventory"},
    )


@app.delete("/items/{item_id}")
def delete_item(item_id: int) -> Response:
    if item_id != 1:
        return JSONResponse(
            content=ErrorResponse(error="item not found").model_dump(),
            status_code=404,
        )
    return Response(status_code=204)


@app.post("/items")
async def create_item(request: Request) -> Response:
    try:
        data = await request.json()
    except Exception:
        data = {}

    if not isinstance(data, dict) or "name" not in data:
        return JSONResponse(
            content=ErrorResponse(error="name is required").model_dump(),
            status_code=400,
        )

    return JSONResponse(
        content=ItemResponse(id=9, name=data["name"]).model_dump(),
        status_code=201,
        headers={"Location": "/items/9"},
    )