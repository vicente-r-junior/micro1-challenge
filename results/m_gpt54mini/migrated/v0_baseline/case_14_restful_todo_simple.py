from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

todos: dict[str, str] = {}


class TodoResponse(BaseModel):
    __root__: dict[str, str]


@app.get("/{todo_id}")
def get_todo(todo_id: str):
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {todo_id: todos[todo_id]}


@app.put("/{todo_id}")
def put_todo(todo_id: str, data: str = Form(...)):
    todos[todo_id] = data
    return {todo_id: todos[todo_id]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")