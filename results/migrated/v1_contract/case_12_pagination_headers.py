'''Pagination advertised through response headers. Synthetic case.

Exercises: RFC 5988 Link headers, X-Total-Count, an out-of-range page that
returns an empty list with 200 rather than 404, and a cap on page size.
'''

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

_EVENTS = [{'id': i, 'kind': 'click'} for i in range(1, 26)]
MAX_PER_PAGE = 10


@app.get('/events')
def events(request: Request):
    # Mimic Flask's request.args.get(key, default, type=int) lenient behavior.
    try:
        page = int(request.query_params.get('page', '1'))
    except (TypeError, ValueError):
        page = 1

    try:
        per_page = int(request.query_params.get('per_page', '5'))
    except (TypeError, ValueError):
        per_page = 5

    if page < 1:
        return JSONResponse(content={'error': 'page must be >= 1'}, status_code=400)
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

    response = JSONResponse(
        content={'events': rows, 'page': page, 'per_page': per_page},
        status_code=200,
    )
    response.headers['X-Total-Count'] = str(total)
    response.headers['Link'] = ', '.join(links)
    return response