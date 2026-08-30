"""Small inventory service migrated from Flask to FastAPI."""

from json import JSONDecodeError
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class Item(BaseModel):
    id: int
    name: str
    qty: Any


class ItemsResponse(BaseModel):
    items: list[Item]
    count: int


class CreateItemResponse(BaseModel):
    id: int
    name: str
    qty: Any


class DeleteResponse(BaseModel):
    deleted: int


class HealthResponse(BaseModel):
    status: str
    page_size: int


class ErrorResponse(BaseModel):
    error: str


app = FastAPI()
app.state.PAGE_SIZE = 2

_ITEMS = {
    1: {"id": 1, "name": "bolt", "qty": 40},
    2: {"id": 2, "name": "nut", "qty": 12},
    3: {"id": 3, "name": "washer", "qty": 7},
}


def _json_error(message: str, status_code: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status_code)


def _is_json_content_type(content_type: str | None) -> bool:
    if not content_type:
        return False
    media_type = content_type.split(";", 1)[0].strip().lower()
    return media_type == "application/json" or (
        media_type.startswith("application/") and media_type.endswith("+json")
    )


def _parse_limit(request: Request) -> int:
    values = request.query_params.getlist("limit")
    if not values:
        return app.state.PAGE_SIZE

    try:
        limit = int(values[0])
    except (TypeError, ValueError):
        return app.state.PAGE_SIZE

    return limit or app.state.PAGE_SIZE


@app.get("/items", response_model=ItemsResponse)
def list_items(request: Request) -> dict[str, Any]:
    limit = _parse_limit(request)
    items = list(_ITEMS.values())[:limit]
    return {"items": items, "count": len(items)}


@app.get(
    "/items/{item_id:int}",
    response_model=Item,
    responses={404: {"model": ErrorResponse}},
)
def get_item(item_id: int) -> dict[str, Any] | JSONResponse:
    item = _ITEMS.get(item_id)
    if item is None:
        return _json_error("item not found", status.HTTP_404_NOT_FOUND)
    return item


@app.post(
    "/items",
    response_model=CreateItemResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}},
)
async def create_item(request: Request) -> dict[str, Any] | JSONResponse:
    if not _is_json_content_type(request.headers.get("content-type")):
        return _json_error("body must be JSON", status.HTTP_400_BAD_REQUEST)

    try:
        data = await request.json()
    except JSONDecodeError:
        return _json_error("body must be JSON", status.HTTP_400_BAD_REQUEST)

    if not data:
        return _json_error("body must be JSON", status.HTTP_400_BAD_REQUEST)
    if "name" not in data:
        return _json_error("name is required", status.HTTP_400_BAD_REQUEST)
    if not isinstance(data["name"], str):
        return _json_error("name must be a string", status.HTTP_400_BAD_REQUEST)

    qty = data.get("qty", 0)
    new_id = max(_ITEMS) + 1
    return {"id": new_id, "name": data["name"], "qty": qty}


@app.delete(
    "/items/{item_id:int}",
    response_model=DeleteResponse,
    responses={404: {"model": ErrorResponse}},
)
def delete_item(item_id: int) -> dict[str, int] | JSONResponse:
    if item_id not in _ITEMS:
        return _json_error("item not found", status.HTTP_404_NOT_FOUND)
    return {"deleted": item_id}


@app.get("/health", response_model=HealthResponse)
def health() -> dict[str, Any]:
    return {"status": "ok", "page_size": app.state.PAGE_SIZE}