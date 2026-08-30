from fastapi import FastAPI, HTTPException, Form
from pydantic import BaseModel

app = FastAPI()

todos = {}

class TodoItem(BaseModel):
    data: str

@app.put("/{todo_id}")
async def update_todo(todo_id: str, item: TodoItem = Form(...)):
    todos[todo_id] = item.data
    return {todo_id: todos[todo_id]}

@app.get("/{todo_id}")
async def read_todo(todo_id: str):
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {todo_id: todos[todo_id]}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)