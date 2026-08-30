from typing import Dict

import uvicorn
from fastapi import FastAPI, Form, HTTPException
from pydantic import BaseModel, ConfigDict

app = FastAPI()

todos: Dict[str, str] = {}


class TodoMap(BaseModel):
    model_config = ConfigDict(extra="allow")


@app.get("/{todo_id}", response_model=TodoMap)
def get_todo(todo_id: str):
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {todo_id: todos[todo_id]}


@app.put("/{todo_id}", response_model=TodoMap)
def put_todo(todo_id: str, data: str = Form(...)):
    todos[todo_id] = data
    return {todo_id: todos[todo_id]}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)