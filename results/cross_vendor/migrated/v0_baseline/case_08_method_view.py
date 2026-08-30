from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

_TASKS = {1: {"id": 1, "title": "write migration", "done": False}}

class Task(BaseModel):
    id: int
    title: str
    done: bool

class TaskCreate(BaseModel):
    title: str

@app.get("/tasks", response_model=List[Task])
async def get_tasks():
    return list(_TASKS.values())

@app.post("/tasks", response_model=Task, status_code=201)
async def create_task(task: TaskCreate):
    task_id = max(_TASKS.keys()) + 1 if _TASKS else 1
    new_task = {"id": task_id, "title": task.title, "done": False}
    _TASKS[task_id] = new_task
    return new_task

@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: int):
    task = _TASKS.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task

@app.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: int, task_update: TaskCreate):
    task = _TASKS.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    updated_task = {**task, "title": task_update.title}
    _TASKS[task_id] = updated_task
    return updated_task

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: int):
    if task_id not in _TASKS:
        raise HTTPException(status_code=404, detail="task not found")
    del _TASKS[task_id]
    return JSONResponse(content={"deleted": task_id})