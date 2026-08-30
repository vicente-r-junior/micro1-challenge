import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

todos = {}


class FlaskStyleJSONResponse(JSONResponse):
    def render(self, content):
        return (json.dumps(content) + "\n").encode("utf-8")


@app.get("/{todo_id}")
def get_todo(todo_id: str):
    try:
        return FlaskStyleJSONResponse({todo_id: todos[todo_id]})
    except KeyError:
        return FlaskStyleJSONResponse(
            {"message": "Internal Server Error"}, status_code=500
        )


@app.put("/{todo_id}")
async def put_todo(todo_id: str, request: Request):
    form = await request.form()
    value = next(
        (item for item in form.getlist("data") if isinstance(item, str)),
        None,
    )
    if value is None:
        return FlaskStyleJSONResponse(
            {"message": "KeyError: 'data'"}, status_code=400
        )
    todos[todo_id] = value
    return FlaskStyleJSONResponse({todo_id: todos[todo_id]})