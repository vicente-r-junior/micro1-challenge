from typing import Annotated

from fastapi import Depends, FastAPI, Form
from pydantic import BaseModel

app = FastAPI()

todos: dict[str, str] = {}


class TodoForm(BaseModel):
    data: str


def parse_todo_form(data: Annotated[str, Form(...)]) -> TodoForm:
    return TodoForm(data=data)


@app.get("/{todo_id}")
def get_todo(todo_id: str) -> dict[str, str]:
    return {todo_id: todos[todo_id]}


@app.put("/{todo_id}")
def put_todo(todo_id: str, form: Annotated[TodoForm, Depends(parse_todo_form)]) -> dict[str, str]:
    todos[todo_id] = form.data
    return {todo_id: todos[todo_id]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5000)