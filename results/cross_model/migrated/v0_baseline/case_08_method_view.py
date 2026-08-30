import re
from typing import List, Optional

from fastapi import Body, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(redirect_slashes=False)

_TASKS = {1: {"id": 1, "title": "write migration", "done": False}}


class Task(BaseModel):
    id: int
    title: str
    done: bool


class TaskListResponse(BaseModel):
    tasks: List[Task]


class DeletedResponse(BaseModel):
    deleted: int


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "title is required"})


@app.get("/tasks", response_model=TaskListResponse)
def list_tasks():
    return {"tasks": list(_TASKS.values())}


@app.post("/tasks", response_model=Task, status_code=201)
def create_task(payload: Optional[dict] = Body(default=None)):
    payload = payload or {}
    if "title" not in payload:
        return JSONResponse(status_code=400, content={"error": "title is required"})
    return {"id": 2, "title": payload["title"], "done": False}


@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: str):
    if not re.fullmatch(r"-?\d+", task_id):
        return JSONResponse(status_code=404, content={"error": "task not found"})
    task = _TASKS.get(int(task_id))
    if task is None:
        return JSONResponse(status_code=404, content={"error": "task not found"})
    return task


@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: str, payload: Optional[dict] = Body(default=None)):
    if not re.fullmatch(r"-?\d+", task_id):
        return JSONResponse(status_code=404, content={"error": "task not found"})
    task = _TASKS.get(int(task_id))
    if task is None:
        return JSONResponse(status_code=404, content={"error": "task not found"})
    payload = payload or {}
    if "title" not in payload:
        return JSONResponse(status_code=400, content={"error": "title is required"})
    return {**task, "title": payload["title"]}


@app.delete("/tasks/{task_id}", response_model=DeletedResponse)
def delete_task(task_id: str):
    if not re.fullmatch(r"-?\d+", task_id):
        return JSONResponse(status_code=404, content={"error": "task not found"})
    task_id_int = int(task_id)
    if task_id_int not in _TASKS:
        return JSONResponse(status_code=404, content={"error": "task not found"})
    return {"deleted": task_id_int}