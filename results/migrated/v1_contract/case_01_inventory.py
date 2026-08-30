"""Small inventory service. Synthetic case, written for this benchmark.

Exercises: JSON body handling, manual validation with explicit 400s, a query
parameter with a default, path converters, and 404 on a missing resource.
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

PAGE_SIZE = 2

_ITEMS = {
    1: {"id": 1, "name": "bolt", "qty": 40},
    2: {"id": 2, "name": "nut", "qty": 12},
    3: {"id": 3, "name": "washer", "qty": 7},
}

FLASK_404_BODY = (
    '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n'
    "<title>Not Found</title>\n"
    "<h1>Not Found</h1>\n"
    "<p>The requested URL was not found on the server. If you entered the URL "
    "manually please check your spelling and try again.</p>"
)

FLASK_405_BODY = (
    '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n'
    "<title>Method Not Allowed</title>\n"
    "<h1>Method Not Allowed</h1>\n"
    "<p>The method is not allowed for the requested URL.</p>"
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return HTMLResponse(content=FLASK_404_BODY, status_code=404)
    if exc.status_code == 405:
        return HTMLResponse(content=FLASK_405_BODY, status_code=405)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def _parse_limit(request: Request) -> int:
    raw = request.query_params.get("limit")
    if raw is None:
        return PAGE_SIZE
    try:
        limit = int(raw)
    except (TypeError, ValueError):
        limit = None
    if not limit:
        return PAGE_SIZE
    return limit


@app.get("/health")
def health():
    return JSONResponse({"status": "ok", "page_size": PAGE_SIZE})


@app.get("/items")
def list_items(request: Request):
    limit = _parse_limit(request)
    items = list(_ITEMS.values())[:limit]
    return JSONResponse({"items": items, "count": len(items)})


@app.get("/items/{item_id:int}")
def get_item(item_id: int):
    item = _ITEMS.get(item_id)
    if item is None:
        return JSONResponse({"error": "item not found"}, status_code=404)
    return JSONResponse(item)


@app.post("/items")
async def create_item(request: Request):
    content_type = request.headers.get("content-type")
    if content_type is None:
        data = None
    else:
        mimetype = content_type.split(";")[0].strip().lower()
        if mimetype != "application/json" and not (
            mimetype.startswith("application/") and mimetype.endswith("+json")
        ):
            data = None
        else:
            try:
                data = await request.json()
            except Exception:
                data = None

    if not data:
        return JSONResponse({"error": "body must be JSON"}, status_code=400)
    if "name" not in data:
        return JSONResponse({"error": "name is required"}, status_code=400)
    if not isinstance(data["name"], str):
        return JSONResponse({"error": "name must be a string"}, status_code=400)
    qty = data.get("qty", 0)
    new_id = max(_ITEMS) + 1
    return JSONResponse(
        {"id": new_id, "name": data["name"], "qty": qty}, status_code=201
    )


@app.delete("/items/{item_id:int}")
def delete_item(item_id: int):
    if item_id not in _ITEMS:
        return JSONResponse({"error": "item not found"}, status_code=404)
    return JSONResponse({"deleted": item_id})