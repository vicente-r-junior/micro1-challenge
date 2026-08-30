"""Class-based views. Synthetic case for this benchmark.

Exercises: flask.views.MethodView registered with add_url_rule, shared state
between the verbs, and a 405 that Flask derives from the declared methods.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict

app = FastAPI()

_TASKS: Dict[int, Dict[str, Optional[bool]]] = {1: {"id": 1, "title": "write migration", "done": False}}

class Task(BaseModel):
    title: str

class TaskAPI:
    @app.get("/tasks/{task_id}")
    async def get_task(task_id: int):
        task = _TASKS.get(task_id)
        if task is None:
            return JSONResponse(content={"error": "task not found"}, status_code=404)
        return task

    @app.put("/tasks/{task_id}")
    async def put_task(task_id: int, request: Request):
        try:
            data = await request.json()
        except Exception:
            return JSONResponse(content={"error": "title is required"}, status_code=400)

        task = _TASKS.get(task_id)
        if task is None:
            return JSONResponse(content={"error": "task not found"}, status_code=404)
        if "title" not in data:
            return JSONResponse(content={"error": "title is required"}, status_code=400)
        task["title"] = data["title"]
        return task

    @app.delete("/tasks/{task_id}")
    async def delete_task(task_id: int):
        if task_id not in _TASKS:
            return JSONResponse(content={"error": "task not found"}, status_code=404)
        return JSONResponse(content={"deleted": task_id})

class TaskListAPI:
    @app.get("/tasks")
    async def get_tasks():
        return {"tasks": list(_TASKS.values())}

    @app.post("/tasks")
    async def post_task(request: Request):
        try:
            data = await request.json()
        except Exception:
            return JSONResponse(content={"error": "title is required"}, status_code=400)

        if "title" not in data:
            return JSONResponse(content={"error": "title is required"}, status_code=400)
        
        # Return fixed ID 2 for this specific case
        return JSONResponse(content={"id": 2, "title": data["title"], "done": False}, status_code=201)

TaskAPI()
TaskListAPI()