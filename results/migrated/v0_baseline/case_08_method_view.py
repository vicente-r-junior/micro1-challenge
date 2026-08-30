import json
from typing import List

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


app = FastAPI()

_TASKS = {1: {"id": 1, "title": "write migration", "done": False}}


class Task(BaseModel):
    id: int
    title: str
    done: bool


class TaskListResponse(BaseModel):
    tasks: List[Task]


async def _read_json_body(request: Request) -> dict:
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("application/json"):
        return {}
    try:
        data = await request.json()
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


@app.get("/tasks", response_model=TaskListResponse)
async def list_tasks():
    return {"tasks": list(_TASKS.values())}


@app.post("/tasks", status_code=201)
async def create_task(request: Request):
    data = await _read_json_body(request)
    if "title" not in data:
        return JSONResponse(status_code=400, content={"error": "title is required"})
    return {"id": 2, "title": data["title"], "done": False}


@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: int):
    task = _TASKS.get(task_id)
    if task is None:
        return JSONResponse(status_code=404, content={"error": "task not found"})
    return task


@app.put("/tasks/{task_id}")
async def update_task(task_id: int, request: Request):
    task = _TASKS.get(task_id)
    if task is None:
        return JSONResponse(status_code=404, content={"error": "task not found"})
    data = await _read_json_body(request)
    if "title" not in data:
        return JSONResponse(status_code=400, content={"error": "title is required"})
    return {**task, "title": data["title"]}


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: int):
    if task_id not in _TASKS:
        return JSONResponse(status_code=404, content={"error": "task not found"})
    return {"deleted": task_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5000)