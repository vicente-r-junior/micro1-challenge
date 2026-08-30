"""FastAPI migration of the legacy Flask inventory service."""

import json
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppConfig(BaseModel):
    PAGE_SIZE: int = 2


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.state.config = AppConfig(PAGE_SIZE=2)

_ITEMS = {
    1: {"id": 1, "name": "bolt", "qty": 40},
    2: {"id": 2, "name": "nut", "qty": 12},
    3: {"id": 3, "name": "washer", "qty": 7},
}


class FlaskJSONResponse(JSONResponse):
    """JSON response rendered like Flask's jsonify: compact, sorted, newline."""

    def render(self, content: Any) -> bytes:
        return (
            json.dumps(
                content,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=True,
            )
            + "\n"
        ).encode("utf-8")


def jsonify(content: Any, status_code: int = 200) -> FlaskJSONResponse:
    return FlaskJSONResponse(content=content, status_code=status_code)


def get_config(request: Request) -> AppConfig:
    return request.app.state.config


def _flask_error_page(status_code: int) -> str:
    pages = {
        404: (
            "404 Not Found",
            "Not Found",
            "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.",
        ),
        405: (
            "405 Method Not Allowed",
            "Method Not Allowed",
            "The method is not allowed for the requested URL.",
        ),
        500: (
            "500 Internal Server Error",
            "Internal Server Error",
            "The server encountered an internal error and was unable to complete your request. Either the server is overloaded or there is an error in the application.",
        ),
    }
    title, heading, description = pages[status_code]
    return (
        "<!doctype html>\n"
        "<html lang=en>\n"
        f"<title>{title}</title>\n"
        f"<h1>{heading}</h1>\n"
        f"<p>{description}</p>\n"
    )


@app.exception_handler(StarletteHTTPException)
async def flask_http_exception_handler(request: Request, exc: StarletteHTTPException) -> HTMLResponse:
    if exc.status_code in {404, 405}:
        return HTMLResponse(
            content=_flask_error_page(exc.status_code),
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )
    return HTMLResponse(content=str(exc.detail), status_code=exc.status_code, headers=getattr(exc, "headers", None))


@app.exception_handler(Exception)
async def flask_internal_error_handler(request: Request, exc: Exception) -> HTMLResponse:
    return HTMLResponse(content=_flask_error_page(500), status_code=500)


def _coerce_limit(raw_value: str | None) -> int | None:
    if raw_value is None:
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def _is_json_request(request: Request) -> bool:
    content_type = request.headers.get("content-type", "")
    mimetype = content_type.split(";", 1)[0].strip().lower()
    return mimetype == "application/json" or (mimetype.startswith("application/") and mimetype.endswith("+json"))


async def _get_json_silent(request: Request) -> Any:
    if not _is_json_request(request):
        return None
    body = await request.body()
    try:
        return json.loads(body)
    except Exception:
        return None


@app.get("/items")
async def list_items(request: Request, config: AppConfig = Depends(get_config)):
    limits = request.query_params.getlist("limit")
    raw_limit = limits[0] if limits else None
    limit = _coerce_limit(raw_limit) or config.PAGE_SIZE
    items = list(_ITEMS.values())[:limit]
    return jsonify({"items": items, "count": len(items)})


@app.get("/items/{item_id:int}")
async def get_item(item_id: int):
    item = _ITEMS.get(item_id)
    if item is None:
        return jsonify({"error": "item not found"}, status_code=404)
    return jsonify(item)


@app.post("/items")
async def create_item(request: Request):
    data = await _get_json_silent(request)
    if not data:
        return jsonify({"error": "body must be JSON"}, status_code=400)
    if "name" not in data:
        return jsonify({"error": "name is required"}, status_code=400)
    if not isinstance(data["name"], str):
        return jsonify({"error": "name must be a string"}, status_code=400)
    qty = data.get("qty", 0)
    new_id = max(_ITEMS) + 1
    return jsonify({"id": new_id, "name": data["name"], "qty": qty}, status_code=201)


@app.delete("/items/{item_id:int}")
async def delete_item(item_id: int):
    if item_id not in _ITEMS:
        return jsonify({"error": "item not found"}, status_code=404)
    return jsonify({"deleted": item_id})


@app.get("/health")
async def health(config: AppConfig = Depends(get_config)):
    return jsonify({"status": "ok", "page_size": config.PAGE_SIZE})