from typing import Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI()

TODOS = {
    'todo1': {'task': 'build an API'},
    'todo2': {'task': '?????'},
    'todo3': {'task': 'profit!'},
}

def abort_if_todo_doesnt_exist(todo_id: str):
    if todo_id not in TODOS:
        raise HTTPException(status_code=404, detail=f"Todo {todo_id} doesn't exist")


class TodoInput(BaseModel):
    task: Optional[str] = None


@app.get("/todos")
async def get_todos():
    return TODOS


@app.post("/todos", status_code=status.HTTP_201_CREATED)
async def create_todo(todo: TodoInput):
    todo_id = f"todo{len(TODOS) + 1}"
    TODOS[todo_id] = {"task": todo.task}
    return TODOS[todo_id]


@app.get("/todos/{todo_id}")
async def get_todo(todo_id: str):
    abort_if_todo_doesnt_exist(todo_id)
    return TODOS[todo_id]


@app.put("/todos/{todo_id}", status_code=status.HTTP_201_CREATED)
async def update_todo(todo_id: str, todo: TodoInput):
    task = {"task": todo.task}
    TODOS[todo_id] = task
    return task


@app.delete("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(todo_id: str):
    abort_if_todo_doesnt_exist(todo_id)
    del TODOS[todo_id]
    return None


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)