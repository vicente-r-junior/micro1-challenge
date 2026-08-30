"""FastAPI migration of the legacy Flask module."""

import json
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

_ROWS = [("1", "bolt", "40"), ("2", "nut", "12")]


class AppConfig(BaseModel):
    """Placeholder Pydantic v2 config model for dependency-injection parity."""

    model_config = ConfigDict(extra="allow")


class FlaskJSONResponse(JSONResponse):
    """JSON response rendered like Flask's jsonify: compact JSON plus newline."""

    def render(self, content: Any) -> bytes:
        return (
            json.dumps(
                content,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")


def _is_json_request(request: Request) -> bool:
    content_type = request.headers.get("content-type", "")
    mimetype = content_type.split(";", 1)[0].strip().lower()
    return mimetype == "application/json" or (
        mimetype.startswith("application/") and mimetype.endswith("+json")
    )


@app.exception_handler(StarletteHTTPException)
async def flask_like_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return Response(
            content=(
                "<!doctype html>\n"
                "<html lang=en>\n"
                "<title>404 Not Found</title>\n"
                "<h1>Not Found</h1>\n"
                "<p>The requested URL was not found on the server. If you entered the URL "
                "manually please check your spelling and try again.</p>\n"
            ),
            status_code=404,
            media_type="text/html; charset=utf-8",
        )
    if exc.status_code == 405:
        return Response(
            content=(
                "<!doctype html>\n"
                "<html lang=en>\n"
                "<title>405 Method Not Allowed</title>\n"
                "<h1>Method Not Allowed</h1>\n"
                "<p>The method is not allowed for the requested URL.</p>\n"
            ),
            status_code=405,
            headers=exc.headers,
            media_type="text/html; charset=utf-8",
        )
    return Response(
        content=str(exc.detail),
        status_code=exc.status_code,
        headers=exc.headers,
        media_type="text/plain; charset=utf-8",
    )


@app.get("/export.csv")
async def export_csv():
    body = "id,name,qty\n" + "\n".join(",".join(row) for row in _ROWS) + "\n"
    return Response(
        content=body,
        status_code=200,
        headers={
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": "attachment; filename=export.csv",
        },
    )


@app.get("/ping")
async def ping():
    return Response(
        content="pong",
        status_code=200,
        headers={
            "Content-Type": "text/plain; charset=utf-8",
            "X-Service": "inventory",
        },
    )


@app.delete("/items/{item_id:int}")
async def delete_item(item_id: int):
    if item_id != 1:
        return FlaskJSONResponse(content={"error": "item not found"}, status_code=404)
    return Response(content="", status_code=204, media_type="text/html; charset=utf-8")


@app.post("/items")
async def create_item(request: Request):
    data: Any = {}
    if _is_json_request(request):
        raw_body = await request.body()
        if raw_body:
            try:
                data = json.loads(raw_body)
            except Exception:
                data = None
    data = data or {}

    if "name" not in data:
        return FlaskJSONResponse(content={"error": "name is required"}, status_code=400)

    return FlaskJSONResponse(
        content={"id": 9, "name": data["name"]},
        status_code=201,
        headers={"Location": "/items/9"},
    )