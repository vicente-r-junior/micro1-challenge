'''Pagination advertised through response headers.

Migrated from Flask to FastAPI.

Exercises: RFC 5988 Link headers, X-Total-Count, an out-of-range page that
returns an empty list with 200 rather than 404, and a cap on page size.
'''

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse

app = FastAPI()

_EVENTS = [{"id": i, "kind": "click"} for i in range(1, 26)]
MAX_PER_PAGE = 10


@app.get("/events")
def events(response: Response, page: int = 1, per_page: int = 5):
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
        links.append(
            f'</events?page={page + 1}&per_page={per_page}>; rel="next"'
        )
    response.headers["Link"] = ", ".join(links)

    return {"events": rows, "page": page, "per_page": per_page}