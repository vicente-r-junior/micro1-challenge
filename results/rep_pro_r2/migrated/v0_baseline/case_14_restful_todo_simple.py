from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from urllib.parse import parse_qs

app = FastAPI()

todos = {}


class TodoUpdate(BaseModel):
    data: str


@app.get("/{todo_id}")
async def get_todo(todo_id: str):
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {todo_id: todos[todo_id]}


@app.put("/{todo_id}")
async def put_todo(todo_id: str, request: Request):
    body = (await request.body()).decode()
    params = parse_qs(body, keep_blank_values=True)
    if "data" not in params:
        raise HTTPException(status_code=400, detail="Missing 'data' form field")
    update = TodoUpdate.model_validate({"data": params["data"][0]})
    todos[todo_id] = update.data
    return {todo_id: update.data}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info")