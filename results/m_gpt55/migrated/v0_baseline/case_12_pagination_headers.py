"""Pagination advertised through response headers. Synthetic case.

Migrated from Flask to FastAPI.
Exercises: RFC 5988 Link headers, X-Total-Count, an out-of-range page that
returns an empty list with 200 rather than 404, and a cap on page size.
"""

from typing import Any

from fastapi import FastAPI, Query, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

app = FastAPI()

_EVENTS = [{"id": i, "kind": "click"} for i in range(1, 26)]
MAX_PER_PAGE = 10


class Event(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str


class EventsResponse(BaseModel):
    events: list[Event]
    page: int
    per_page: int


@app.get("/events", response_model=EventsResponse)
def events(
    response: Response,
    page: int = Query(default=1),
    per_page: int = Query(default=5),
) -> Any:
    if page < 1:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "page must be >= 1"},
        )

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

    return EventsResponse(events=rows, page=page, per_page=per_page)