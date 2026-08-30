from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI()

TODOS = {
    'todo1': {'task': 'build an API'},
    'todo2': {'task': '?????'},
    'todo3': {'task': 'profit!'},
}


class TodoItem(BaseModel):
    task: str | None = None


class TodoResponse(BaseModel):
    task: str


class TodoCreate(BaseModel):
    task: str | None = None


class TodoUpdate(BaseModel):
    task: str | None = None


def abort_if_todo_doesnt_exist(todo_id: str) -> None:
    if todo_id not in TODOS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo {todo_id} doesn't exist",
        )


@app.get('/todos')
def get_todos():
    return TODOS


@app.post('/todos', status_code=status.HTTP_201_CREATED)
def create_todo(payload: TodoCreate):
    todo_id = 'todo%d' % (len(TODOS) + 1)
    TODOS[todo_id] = {'task': payload.task}
    return TODOS[todo_id]


@app.get('/todos/{todo_id}')
def get_todo(todo_id: str):
    abort_if_todo_doesnt_exist(todo_id)
    return TODOS[todo_id]


@app.delete('/todos/{todo_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: str):
    abort_if_todo_doesnt_exist(todo_id)
    del TODOS[todo_id]
    return None


@app.put('/todos/{todo_id}', status_code=status.HTTP_201_CREATED)
def update_todo(todo_id: str, payload: TodoUpdate):
    task = {'task': payload.task}
    TODOS[todo_id] = task
    return task


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='127.0.0.1', port=8000, reload=True)