from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

_EVENTS = [{'id': i, 'kind': 'click'} for i in range(1, 26)]
MAX_PER_PAGE = 10


@app.get('/events')
def events(request: Request):
    page_values = request.query_params.getlist('page')
    per_page_values = request.query_params.getlist('per_page')

    page_raw = page_values[0] if page_values else None
    per_page_raw = per_page_values[0] if per_page_values else None

    if page_raw is None:
        page = 1
    else:
        try:
            page = int(page_raw)
        except (ValueError, TypeError):
            page = 1

    if per_page_raw is None:
        per_page = 5
    else:
        try:
            per_page = int(per_page_raw)
        except (ValueError, TypeError):
            per_page = 5

    if page < 1:
        return JSONResponse(content={'error': 'page must be >= 1'}, status_code=400)

    if per_page > MAX_PER_PAGE:
        per_page = MAX_PER_PAGE

    start = (page - 1) * per_page
    rows = _EVENTS[start : start + per_page]
    total = len(_EVENTS)
    last_page = (total + per_page - 1) // per_page

    links = [f'</events?page=1&per_page={per_page}>; rel="first"',
             f'</events?page={last_page}&per_page={per_page}>; rel="last"']
    if page < last_page:
        links.append(f'</events?page={page + 1}&per_page={per_page}>; rel="next"')

    return JSONResponse(
        content={'events': rows, 'page': page, 'per_page': per_page},
        status_code=200,
        headers={'X-Total-Count': str(total), 'Link': ', '.join(links)},
    )