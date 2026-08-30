from typing import Dict, Optional

from fastapi import FastAPI, Form, HTTPException
from pydantic import RootModel

app = FastAPI()

todos = {}

class TodoMap(RootModel[Dict[str, str]]):
    pass

@app.get("/{todo_id}", response_model=TodoMap)
def get_todo(todo_id: str):
    return {todo_id: todos[todo_id]}

@app.put("/{todo_id}", response_model=TodoMap)
def put_todo(todo_id: str, data: Optional[str] = Form(None)):
    if data is None:
        raise HTTPException(status_code=400, detail="Bad Request")
    todos[todo_id] = data
    return {todo_id: data}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5000)