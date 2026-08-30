from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import json
import re

app = FastAPI()

_TASKS = {1: {"id": 1, "title": "write migration", "done": False}}


async def _read_json_body(request: Request):
    content_type = request.headers.get("content-type", "")
    mimetype = content_type.split(";")[0].strip().lower()
    if mimetype != "application/json" and not (mimetype.endswith("+json") and "/" in mimetype):
        return {}
    raw = await request.body()
    if not raw:
        return {}
    try:
        body = json.loads(raw)
    except ValueError:
        return {}
    return body or {}


def _to_task_id(task_id: str):
    if not re.fullmatch(r"\d+", task_id):
        return None
    try:
        return int(task_id)
    except ValueError:
        return None


@app.get("/tasks")
def list_tasks():
    return JSONResponse(content={"tasks": list(_TASKS.values())})


@app.post("/tasks")
async def create_task(request: Request):
    data = await _read_json_body(request)
    if "title" not in data:
        return JSONResponse(content={"error": "title is required"}, status_code=400)
    return JSONResponse(content={"id": 2, "title": data["title"], "done": False}, status_code=201)


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    task_id_int = _to_task_id(task_id)
    if task_id_int is None:
        return JSONResponse(content={"error": "task not found"}, status_code=404)
    task = _TASKS.get(task_id_int)
    if task is None:
        return JSONResponse(content={"error": "task not found"}, status_code=404)
    return JSONResponse(content=task)


@app.put("/tasks/{task_id}")
async def update_task(task_id: str, request: Request):
    task_id_int = _to_task_id(task_id)
    if task_id_int is None:
        return JSONResponse(content={"error": "task not found"}, status_code=404)
    task = _TASKS.get(task_id_int)
    if task is None:
        return JSONResponse(content={"error": "task not found"}, status_code=404)
    data = await _read_json_body(request)
    if "title" not in data:
        return JSONResponse(content={"error": "title is required"}, status_code=400)
    return JSONResponse(content={**task, "title": data["title"]})


@app.delete("/tasks/{task_id}")
def delete_task(task_id: str):
    task_id_int = _to_task_id(task_id)
    if task_id_int is None:
        return JSONResponse(content={"error": "task not found"}, status_code=404)
    if task_id_int not in _TASKS:
        return JSONResponse(content={"error": "task not found"}, status_code=404)
    return JSONResponse(content={"deleted": task_id_int})