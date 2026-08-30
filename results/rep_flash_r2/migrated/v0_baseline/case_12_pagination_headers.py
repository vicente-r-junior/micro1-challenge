from fastapi import FastAPI, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI()

_EVENTS = [{"id": i, "kind": "click"} for i in range(1, 26)]
MAX_PER_PAGE = 10

class Event(BaseModel):
    id: int
    kind: str

class EventsResponse(BaseModel):
    events: list[Event]
    page: int
    per_page: int

@app.get("/events", response_model=EventsResponse)
def events(response: Response, page: int = Query(1), per_page: int = Query(5)):
    if page < 1:
        return JSONResponse(status_code=400, content={"error": "page must be >= 1"})
    if per_page > MAX_PER_PAGE:
        per_page = MAX_PER_PAGE

    start = (page - 1) * per_page
    rows = _EVENTS[start : start + per_page]
    total = len(_EVENTS)
    last_page = (total + per_page - 1) // per_page

    response.headers["X-Total-Count"] = str(total)
    links = [
        f'</events?page=1&per_page={per_page}>; rel="first"',
        f'</events?page={last_page}&per_page={per_page}>; rel="last"',
    ]
    if page < last_page:
        links.append(f'</events?page={page + 1}&per_page={per_page}>; rel="next"')
    response.headers["Link"] = ", ".join(links)
    return {"events": rows, "page": page, "per_page": per_page}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)