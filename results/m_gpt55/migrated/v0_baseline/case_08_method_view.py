"""Class-based Flask MethodView example migrated to FastAPI.

Exercises: multiple HTTP verbs on the same paths, shared state between verbs,
and FastAPI/Starlette-derived 405 responses for undeclared methods.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, ValidationError

app = FastAPI()

_TASKS: dict[int, dict[str, Any]] = {
    1: {"id": 1, "title": "write migration", "done": False}
}


class TaskModel(BaseModel):
    id: int
    title: Any
    done: bool


class TaskListModel(BaseModel):
    tasks: list[TaskModel]


class ErrorModel(BaseModel):
    error: str


class DeleteModel(BaseModel):
    deleted: int


class TitlePayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: Any


async def get_json_silent(request: Request) -> Any:
    try:
        data = await request.json()
    except Exception:
        return {}
    return data or {}


def error_response(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorModel(error=message).model_dump(),
    )


@app.get("/tasks")
async def list_tasks() -> dict[str, Any]:
    return TaskListModel(tasks=list(_TASKS.values())).model_dump()


@app.post("/tasks")
async def create_task(request: Request) -> JSONResponse:
    data = await get_json_silent(request)
    try:
        payload = TitlePayload.model_validate(data)
    except ValidationError:
        return error_response("title is required", 400)

    task = TaskModel(id=2, title=payload.title, done=False)
    return JSONResponse(status_code=201, content=task.model_dump())


@app.get("/tasks/{task_id}")
async def get_task(task_id: int) -> dict[str, Any] | JSONResponse:
    task = _TASKS.get(task_id)
    if task is None:
        return error_response("task not found", 404)
    return TaskModel.model_validate(task).model_dump()


@app.put("/tasks/{task_id}")
async def update_task(task_id: int, request: Request) -> dict[str, Any] | JSONResponse:
    task = _TASKS.get(task_id)
    if task is None:
        return error_response("task not found", 404)

    data = await get_json_silent(request)
    try:
        payload = TitlePayload.model_validate(data)
    except ValidationError:
        return error_response("title is required", 400)

    return TaskModel.model_validate({**task, "title": payload.title}).model_dump()


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: int) -> dict[str, int] | JSONResponse:
    if task_id not in _TASKS:
        return error_response("task not found", 404)
    return DeleteModel(deleted=task_id).model_dump()