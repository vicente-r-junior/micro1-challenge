from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

_TASKS = {1: {"id": 1, "title": "write migration", "done": False}}

class Task(BaseModel):
    id: int
    title: str
    done: bool

class TaskListResponse(BaseModel):
    tasks: list[Task]

class DeletedResponse(BaseModel):
    deleted: int

async def _json_or_empty(request: Request) -> Any:
    try:
        data = await request.json()
    except Exception:
        return {}
    return data if data is not None else {}

@app.get("/tasks", response_model=TaskListResponse)
def list_tasks():
    return {"tasks": list(_TASKS.values())}

@app.post("/tasks", status_code=status.HTTP_201_CREATED)
async def create_task(request: Request):
    data = await _json_or_empty(request)
    if not isinstance(data, dict) or "title" not in data:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": "title is required"})
    return {"id": 2, "title": data["title"], "done": False}

@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int):
    task = _TASKS.get(task_id)
    if task is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "task not found"})
    return task

@app.put("/tasks/{task_id}")
async def update_task(task_id: int, request: Request):
    task = _TASKS.get(task_id)
    if task is None:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "task not found"})
    data = await _json_or_empty(request)
    if not isinstance(data, dict) or "title" not in data:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": "title is required"})
    return {**task, "title": data["title"]}

@app.delete("/tasks/{task_id}", response_model=DeletedResponse)
def delete_task(task_id: int):
    if task_id not in _TASKS:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "task not found"})
    return {"deleted": task_id}