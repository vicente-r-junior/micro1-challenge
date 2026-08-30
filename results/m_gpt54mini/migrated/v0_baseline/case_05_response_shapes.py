from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse, Response as FastAPIResponse
from pydantic import BaseModel

app = FastAPI()

_ROWS = [("1", "bolt", "40"), ("2", "nut", "12")]


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
    return PlainTextResponse(
        content="pong",
        media_type="text/plain; charset=utf-8",
        headers={"X-Service": "inventory"},
    )


@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    if item_id != 1:
        return JSONResponse({"error": "item not found"}, status_code=404)
    return FastAPIResponse(status_code=204)


@app.post("/items")
async def create_item(request: Request):
    try:
        data = await request.json()
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}

    if "name" not in data:
        return JSONResponse({"error": "name is required"}, status_code=400)

    response = JSONResponse({"id": 9, "name": data["name"]}, status_code=201)
    response.headers["Location"] = "/items/9"
    return response