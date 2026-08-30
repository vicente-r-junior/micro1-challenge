from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.status import HTTP_200_OK

app = FastAPI()

todos = {}


@app.get("/{todo_id}")
async def get_todo(todo_id: str):
    try:
        return {todo_id: todos[todo_id]}
    except KeyError:
        return JSONResponse(content={"error": "not found"}, status_code=404)


@app.put("/{todo_id}")
async def put_todo(todo_id: str, request: Request):
    form = await request.form()
    todos[todo_id] = form["data"]
    return {todo_id: todos[todo_id]}