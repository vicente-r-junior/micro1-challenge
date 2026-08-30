from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

app = FastAPI()

_EVENTS = [{"id": i, "kind": "click"} for i in range(1, 26)]
MAX_PER_PAGE = 10


@app.get("/events")
def events(page: int = Query(1), per_page: int = Query(5)) -> JSONResponse:
    if page < 1:
        return JSONResponse({"error": "page must be >= 1"}, status_code=400)

    if per_page > MAX_PER_PAGE:
        per_page = MAX_PER_PAGE

    start = (page - 1) * per_page
    rows = _EVENTS[start : start + per_page]
    total = len(_EVENTS)
    last_page = (total + per_page - 1) // per_page

    links = [
        f'</events?page=1&per_page={per_page}>; rel="first"',
        f'</events?page={last_page}&per_page={per_page}>; rel="last"',
    ]
    if page < last_page:
        links.append(f'</events?page={page + 1}&per_page={per_page}>; rel="next"')

    headers = {
        "X-Total-Count": str(total),
        "Link": ", ".join(links),
    }
    return JSONResponse(
        {"events": rows, "page": page, "per_page": per_page},
        status_code=200,
        headers=headers,
    )