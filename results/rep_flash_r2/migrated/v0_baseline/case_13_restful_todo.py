from typing import Optional
import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

TODOS = {
    'todo1': {'task': 'build an API'},
    'todo2': {'task': '?????'},
    'todo3': {'task': 'profit!'},
}

class TodoIn(BaseModel):
    task: Optional[str] = None

def abort_if_todo_doesnt_exist(todo_id: str) -> None:
    if todo_id not in TODOS:
        raise HTTPException(status_code=404, detail=f"Todo {todo_id} doesn't exist")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={'message': exc.detail},
        headers=exc.headers,
    )

@app.get('/todos')
def list_todos():
    return TODOS

@app.post('/todos', status_code=status.HTTP_201_CREATED)
def create_todo(item: Optional[TodoIn] = None, task: Optional[str] = None):
    if item is not None and item.task is not None:
        task = item.task
    todo_id = f'todo{len(TODOS) + 1}'
    TODOS[todo_id] = {'task': task}
    return TODOS[todo_id]

@app.get('/todos/{todo_id}')
def get_todo(todo_id: str):
    abort_if_todo_doesnt_exist(todo_id)
    return TODOS[todo_id]

@app.put('/todos/{todo_id}', status_code=status.HTTP_201_CREATED)
def put_todo(todo_id: str, item: Optional[TodoIn] = None, task: Optional[str] = None):
    abort_if_todo_doesnt_exist(todo_id)
    if item is not None and item.task is not None:
        task = item.task
    TODOS[todo_id] = {'task': task}
    return TODOS[todo_id]

@app.delete('/todos/{todo_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: str):
    abort_if_todo_doesnt_exist(todo_id)
    del TODOS[todo_id]
    return None

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=5000)