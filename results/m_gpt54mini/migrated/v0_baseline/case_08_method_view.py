from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel

app = FastAPI()

_TASKS = {1: {"id": 1, "title": "write migration", "done": False}}


class Task(BaseModel):
    id: int
    title: str
    done: bool


class TaskCreate(BaseModel):
    title: str


@app.get("/tasks")
def get_tasks():
    return {"tasks": list(_TASKS.values())}


@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate):
    return {"id": 2, "title": payload.title, "done": False}


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    task = _TASKS.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@app.put("/tasks/{task_id}")
def update_task(task_id: int, request: Request):
    task = _TASKS.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")

    data = request.json()
    if hasattr(data, "__await__"):
        async def _await_json():
            return await data
        return _await_json()

    if "title" not in data:
        raise HTTPException(status_code=400, detail="title is required")
    return {**task, "title": data["title"]}


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    if task_id not in _TASKS:
        raise HTTPException(status_code=404, detail="task not found")
    return {"deleted": task_id}