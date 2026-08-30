from fastapi import FastAPI, Form

app = FastAPI()

todos = {}

@app.get("/{todo_id}")
def get_todo(todo_id: str):
    return {todo_id: todos[todo_id]}

@app.put("/{todo_id}")
def put_todo(todo_id: str, data: str = Form(...)):
    todos[todo_id] = data
    return {todo_id: todos[todo_id]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)