import json
import re
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

PAGE_SIZE = 2

_ITEMS = {
    1: {"id": 1, "name": "bolt", "qty": 40},
    2: {"id": 2, "name": "nut", "qty": 12},
    3: {"id": 3, "name": "washer", "qty": 7},
}

_FLASK_404_HTML = (
    "<!doctype html>\n"
    "<html lang=en>\n"
    "<title>404 Not Found</title>\n"
    "<h1>Not Found</h1>\n"
    "<p>The requested URL was not found on the server. If you entered the URL manually "
    "please check your spelling and try again.</p>\n"
)

_FLASK_405_HTML = (
    "<!doctype html>\n"
    "<html lang=en>\n"
    "<title>405 Method Not Allowed</title>\n"
    "<h1>Method Not Allowed</h1>\n"
    "<p>The method is not allowed for the requested URL.</p>\n"
)

def get_config() -> dict:
    return {"PAGE_SIZE": PAGE_SIZE}

def _jsonify(data, status_code=200):
    body = json.dumps(data, ensure_ascii=True, sort_keys=True)
    return Response(
        content=body + "\n",
        status_code=status_code,
        headers={"Content-Type": "application/json"},
    )

async def _read_json_body(request: Request):
    content_type = request.headers.get("content-type", "")
    mimetype = content_type.split(";", 1)[0].strip().lower()
    if mimetype != "application/json" and not (
        mimetype.startswith("application/") and mimetype.endswith("+json")
    ):
        return None
    try:
        return json.loads(await request.body())
    except ValueError:
        return None

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

@app.exception_handler(StarletteHTTPException)
async def flask_http_exception_handler(request, exc):
    if exc.status_code == 404:
        return HTMLResponse(_FLASK_404_HTML, status_code=404)
    if exc.status_code == 405:
        return HTMLResponse(_FLASK_405_HTML, status_code=405)
    return Response(
        content=json.dumps({"detail": exc.detail}, ensure_ascii=False),
        status_code=exc.status_code,
        headers={"Content-Type": "application/json"},
    )

@app.get("/health")
async def health(config: dict = Depends(get_config)):
    return _jsonify({"status": "ok", "page_size": config["PAGE_SIZE"]})

@app.get("/items")
async def list_items(request: Request, config: dict = Depends(get_config)):
    limit = request.query_params.get("limit")
    if limit is not None:
        try:
            limit = int(limit)
        except ValueError:
            limit = None
    limit = limit or config["PAGE_SIZE"]
    items = list(_ITEMS.values())[:limit]
    return _jsonify({"items": items, "count": len(items)})

@app.post("/items")
async def create_item(request: Request):
    data = await _read_json_body(request)
    if not data:
        return _jsonify({"error": "body must be JSON"}, 400)
    if "name" not in data:
        return _jsonify({"error": "name is required"}, 400)
    if not isinstance(data["name"], str):
        return _jsonify({"error": "name must be a string"}, 400)
    qty = data.get("qty", 0)
    new_id = max(_ITEMS) + 1
    return _jsonify({"id": new_id, "name": data["name"], "qty": qty}, 201)

def _item_id_from_path(item_id: str):
    if re.fullmatch(r"\d+", item_id) is None:
        return None
    return int(item_id)

@app.get("/items/{item_id}")
async def get_item(item_id: str):
    parsed = _item_id_from_path(item_id)
    if parsed is None:
        return HTMLResponse(_FLASK_404_HTML, status_code=404)
    item = _ITEMS.get(parsed)
    if item is None:
        return _jsonify({"error": "item not found"}, 404)
    return _jsonify(item)

@app.delete("/items/{item_id}")
async def delete_item(item_id: str):
    parsed = _item_id_from_path(item_id)
    if parsed is None:
        return HTMLResponse(_FLASK_404_HTML, status_code=404)
    if parsed not in _ITEMS:
        return _jsonify({"error": "item not found"}, 404)
    return _jsonify({"deleted": parsed})