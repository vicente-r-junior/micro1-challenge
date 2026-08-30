import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI()

_ROWS = [("1", "bolt", "40"), ("2", "nut", "12")]


@app.get("/export.csv")
def export_csv():
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
def ping():
    return Response(
        content="pong",
        status_code=200,
        headers={
            "Content-Type": "text/plain; charset=utf-8",
            "X-Service": "inventory",
        },
    )


@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    if item_id != 1:
        return JSONResponse(content={"error": "item not found"}, status_code=404)
    return Response(content="", status_code=204, media_type="text/html")


@app.post("/items")
async def create_item(request: Request):
    content_type = request.headers.get("content-type", "")
    mimetype = content_type.split(";", 1)[0].strip().lower() if content_type else ""
    is_json = mimetype == "application/json" or (
        mimetype.startswith("application/") and mimetype.endswith("+json")
    )

    data = None
    if is_json:
        try:
            data = json.loads(await request.body())
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = None

    data = data or {}
    if "name" not in data:
        return JSONResponse(content={"error": "name is required"}, status_code=400)

    return JSONResponse(
        content={"id": 9, "name": data["name"]},
        status_code=201,
        headers={"Location": "/items/9"},
    )