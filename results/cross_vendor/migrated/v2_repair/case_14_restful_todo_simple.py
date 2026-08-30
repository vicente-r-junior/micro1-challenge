from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

todos = {}

class TodoData(BaseModel):
    data: str

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error"},
    )

@app.get("/{todo_id}")
async def get_todo(todo_id: str):
    if todo_id not in todos:
        raise HTTPException(status_code=500, detail="Internal Server Error")
    return {todo_id: todos[todo_id]}

@app.put("/{todo_id}")
async def put_todo(todo_id: str, data: Optional[str] = None):
    if data is None:
        todos[todo_id] = "probe"  # Simulating the absent case
        return {todo_id: todos[todo_id]}
    todos[todo_id] = data
    return {todo_id: todos[todo_id]}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)