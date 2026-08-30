from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

app = FastAPI()

TODOS = {
    "todo1": {"task": "build an API"},
    "todo2": {"task": "?????"},
    "todo3": {"task": "profit!"},
}


class TodoPayload(BaseModel):
    task: Optional[str] = None


class TodoNotFoundError(Exception):
    def __init__(self, todo_id: str):
        self.message = f"Todo {todo_id} doesn't exist"
        super().__init__(self.message)


@app.exception_handler(TodoNotFoundError)
async def todo_not_found_handler(request: Request, exc: TodoNotFoundError):
    return JSONResponse(status_code=404, content={"message": exc.message})


def abort_if_todo_doesnt_exist(todo_id: str) -> None:
    if todo_id not in TODOS:
        raise TodoNotFoundError(todo_id)


@app.get("/todos/{todo_id}")
def get_todo(todo_id: str):
    abort_if_todo_doesnt_exist(todo_id)
    return TODOS[todo_id]


@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: str):
    abort_if_todo_doesnt_exist(todo_id)
    del TODOS[todo_id]
    return Response(status_code=204)


@app.put("/todos/{todo_id}", status_code=201)
def put_todo(todo_id: str, payload: Optional[TodoPayload] = None):
    task = payload.task if payload is not None else None
    TODOS[todo_id] = {"task": task}
    return TODOS[todo_id]


@app.post("/todos", status_code=201)
def post_todo(payload: Optional[TodoPayload] = None):
    todo_id = f"todo{len(TODOS) + 1}"
    task = payload.task if payload is not None else None
    TODOS[todo_id] = {"task": task}
    return TODOS[todo_id]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)