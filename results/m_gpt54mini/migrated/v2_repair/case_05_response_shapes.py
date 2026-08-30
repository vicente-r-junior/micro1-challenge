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
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=export.csv"},
    )


@app.get("/ping")
def ping():
    return Response(
        content="pong",
        status_code=200,
        media_type="text/plain; charset=utf-8",
        headers={"X-Service": "inventory"},
    )


@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    if item_id != 1:
        return JSONResponse(content={"error": "item not found"}, status_code=404)
    return Response(content="", status_code=204)


@app.post("/items")
async def create_item(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    if "name" not in data:
        return JSONResponse(content={"error": "name is required"}, status_code=400)
    response = JSONResponse(content={"id": 9, "name": data["name"]}, status_code=201)
    response.headers["Location"] = "/items/9"
    return response