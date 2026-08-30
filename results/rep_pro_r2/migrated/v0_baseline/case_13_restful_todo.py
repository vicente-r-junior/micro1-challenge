from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel

app = FastAPI()

TODOS = {
    'todo1': {'task': 'build an API'},
    'todo2': {'task': '?????'},
    'todo3': {'task': 'profit!'},
}


def abort_if_todo_doesnt_exist(todo_id: str):
    if todo_id not in TODOS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo {todo_id} doesn't exist",
        )


class TodoPayload(BaseModel):
    task: Optional[str] = None


async def parse_todo_payload(request: Request) -> TodoPayload:
    content_type = request.headers.get("content-type", "")
    try:
        if "application/json" in content_type:
            data = await request.json()
        else:
            data = await request.form()
    except Exception:
        data = {}

    if isinstance(data, dict):
        task = data.get("task")
    elif hasattr(data, "get"):
        task = data.get("task")
    else:
        task = None

    return TodoPayload(task=task)


@app.get("/todos")
def get_todos():
    return TODOS


@app.post("/todos", status_code=status.HTTP_201_CREATED)
def post_todo(payload: TodoPayload = Depends(parse_todo_payload)):
    todo_id = 'todo%d' % (len(TODOS) + 1)
    TODOS[todo_id] = {'task': payload.task}
    return TODOS[todo_id]


@app.get("/todos/{todo_id}")
def get_todo(todo_id: str):
    abort_if_todo_doesnt_exist(todo_id)
    return TODOS[todo_id]


@app.put("/todos/{todo_id}", status_code=status.HTTP_201_CREATED)
def put_todo(todo_id: str, payload: TodoPayload = Depends(parse_todo_payload)):
    abort_if_todo_doesnt_exist(todo_id)
    task = {'task': payload.task}
    TODOS[todo_id] = task
    return task


@app.delete("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: str):
    abort_if_todo_doesnt_exist(todo_id)
    del TODOS[todo_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)


if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8000)