from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()


class Task(BaseModel):
    id: int
    title: str
    done: bool


_TASKS: dict[int, Task] = {
    1: Task(id=1, title="write migration", done=False)
}


async def _parse_body(request: Request) -> dict:
    try:
        data = await request.json()
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


@app.get("/tasks")
async def list_tasks():
    return {"tasks": [task.model_dump() for task in _TASKS.values()]}


@app.post("/tasks", status_code=201)
async def create_task(request: Request):
    data = await _parse_body(request)
    if "title" not in data:
        return JSONResponse({"error": "title is required"}, status_code=400)
    return JSONResponse({"id": 2, "title": data["title"], "done": False}, status_code=201)


@app.get("/tasks/{task_id}")
async def get_task(task_id: int):
    task = _TASKS.get(task_id)
    if task is None:
        return JSONResponse({"error": "task not found"}, status_code=404)
    return task.model_dump()


@app.put("/tasks/{task_id}")
async def update_task(task_id: int, request: Request):
    task = _TASKS.get(task_id)
    if task is None:
        return JSONResponse({"error": "task not found"}, status_code=404)
    data = await _parse_body(request)
    if "title" not in data:
        return JSONResponse({"error": "title is required"}, status_code=400)
    updated = {**task.model_dump(), "title": data["title"]}
    return updated


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: int):
    if task_id not in _TASKS:
        return JSONResponse({"error": "task not found"}, status_code=404)
    return {"deleted": task_id}