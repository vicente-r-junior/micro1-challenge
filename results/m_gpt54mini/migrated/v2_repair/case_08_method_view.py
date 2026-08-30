from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

_TASKS = {1: {"id": 1, "title": "write migration", "done": False}}


@app.get("/tasks")
def get_tasks():
    return JSONResponse(content={"tasks": list(_TASKS.values())})


@app.post("/tasks")
async def create_task(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    if "title" not in data:
        return JSONResponse(content={"error": "title is required"}, status_code=400)
    return JSONResponse(content={"id": 2, "title": data["title"], "done": False}, status_code=201)


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    task = _TASKS.get(task_id)
    if task is None:
        return JSONResponse(content={"error": "task not found"}, status_code=404)
    return JSONResponse(content=task)


@app.put("/tasks/{task_id}")
async def update_task(task_id: int, request: Request):
    task = _TASKS.get(task_id)
    if task is None:
        return JSONResponse(content={"error": "task not found"}, status_code=404)
    try:
        data = await request.json()
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    if "title" not in data:
        return JSONResponse(content={"error": "title is required"}, status_code=400)
    return JSONResponse(content={**task, "title": data["title"]})


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    if task_id not in _TASKS:
        return JSONResponse(content={"error": "task not found"}, status_code=404)
    return JSONResponse(content={"deleted": task_id})