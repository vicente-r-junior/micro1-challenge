from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional

app = FastAPI()

TODOS: Dict[str, Dict[str, Any]] = {
    'todo1': {'task': 'build an API'},
    'todo2': {'task': '?????'},
    'todo3': {'task': 'profit!'},
}

class TodoItem(BaseModel):
    task: Optional[str] = None

def abort_if_todo_doesnt_exist(todo_id: str):
    if todo_id not in TODOS:
        return JSONResponse(content={'message': 'Todo {} doesn\'t exist'.format(todo_id)}, status_code=404)

@app.get('/todos')
async def get_todos():
    return TODOS

@app.post('/todos', response_model=TodoItem, status_code=201)
async def create_todo(item: TodoItem):
    todo_id = 'todo{}'.format(len(TODOS) + 1)
    task_value = str(item.task) if item.task is not None else None  # Ensure task is a string or None
    TODOS[todo_id] = {'task': task_value}
    return TODOS[todo_id]

@app.get('/todos/{todo_id}', response_model=TodoItem)
async def get_todo(todo_id: str):
    error_response = abort_if_todo_doesnt_exist(todo_id)
    if error_response:
        return error_response
    return TODOS[todo_id]

@app.delete('/todos/{todo_id}', status_code=204)
async def delete_todo(todo_id: str):
    error_response = abort_if_todo_doesnt_exist(todo_id)
    if error_response:
        return error_response
    del TODOS[todo_id]
    return JSONResponse(content='', status_code=204)

@app.put('/todos/{todo_id}', response_model=TodoItem, status_code=201)
async def update_todo(todo_id: str, item: TodoItem):
    error_response = abort_if_todo_doesnt_exist(todo_id)
    if error_response:
        return error_response
    TODOS[todo_id] = {'task': item.task}
    return TODOS[todo_id]

# Handle malformed JSON
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    if exc.status_code == 422:
        return JSONResponse(content={'message': 'The browser (or proxy) sent a request that this server could not understand.'}, status_code=400)
    return await default_http_exception_handler(request, exc)