from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

app = FastAPI()

TODOS: dict[str, dict[str, str | None]] = {
    "todo1": {"task": "build an API"},
    "todo2": {"task": "?????"},
    "todo3": {"task": "profit!"},
}


class TodoNotFound(Exception):
    def __init__(self, todo_id: str) -> None:
        self.todo_id = todo_id
        super().__init__(f"Todo {todo_id} doesn't exist")


class TodoPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    task: str | None = None


@app.exception_handler(TodoNotFound)
async def todo_not_found_handler(request: Request, exc: TodoNotFound) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"message": str(exc)})


def abort_if_todo_doesnt_exist(todo_id: str) -> None:
    if todo_id not in TODOS:
        raise TodoNotFound(todo_id)


async def parse_args(request: Request) -> TodoPayload:
    data: dict[str, Any] = {}
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception:
            body = None
        if isinstance(body, dict):
            data.update(body)
    elif (
        "application/x-www-form-urlencoded" in content_type
        or "multipart/form-data" in content_type
    ):
        form = await request.form()
        data.update(dict(form))

    if "task" not in data and "task" in request.query_params:
        data["task"] = request.query_params["task"]

    return TodoPayload.model_validate(data)


@app.get("/todos/{todo_id}")
async def get_todo(todo_id: str) -> dict[str, str | None]:
    abort_if_todo_doesnt_exist(todo_id)
    return TODOS[todo_id]


@app.delete("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(todo_id: str) -> Response:
    abort_if_todo_doesnt_exist(todo_id)
    del TODOS[todo_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.put("/todos/{todo_id}", status_code=status.HTTP_201_CREATED)
async def put_todo(todo_id: str, request: Request) -> dict[str, str | None]:
    args = await parse_args(request)
    task = {"task": args.task}
    TODOS[todo_id] = task
    return task


@app.get("/todos")
async def get_todos() -> dict[str, dict[str, str | None]]:
    return TODOS


@app.post("/todos", status_code=status.HTTP_201_CREATED)
async def post_todo(request: Request) -> dict[str, str | None]:
    args = await parse_args(request)
    todo_id = "todo%d" % (len(TODOS) + 1)
    TODOS[todo_id] = {"task": args.task}
    return TODOS[todo_id]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)