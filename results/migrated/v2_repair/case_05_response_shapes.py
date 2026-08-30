'''Responses that are not plain JSON. Synthetic case for this benchmark.

Exercises: make_response, text/plain and text/csv bodies, custom headers, a 204
with no content, and a redirect. Migrations tend to JSON-ify all of it.
'''

import json

from fastapi import FastAPI, Request, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, redirect_slashes=False)

_ROWS = [('1', 'bolt', '40'), ('2', 'nut', '12')]

_FLASK_404_HTML = (
    '<!doctype html>' + chr(10) +
    '<html lang=en>' + chr(10) +
    '<title>404 Not Found</title>' + chr(10) +
    '<h1>Not Found</h1>' + chr(10) +
    '<p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.</p>' +
    chr(10)
)


def _json_response(obj, status_code, headers=None):
    if headers is None:
        headers = {}
    headers = dict(headers)
    headers['Content-Type'] = 'application/json'
    return Response(
        content=json.dumps(obj, ensure_ascii=True, separators=(',', ':')),
        status_code=status_code,
        headers=headers,
    )


@app.exception_handler(StarletteHTTPException)
async def _http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return Response(
            content=_FLASK_404_HTML,
            status_code=404,
            headers={'Content-Type': 'text/html; charset=utf-8'},
        )
    return Response(
        content=str(exc.detail),
        status_code=exc.status_code,
        headers={'Content-Type': 'text/plain; charset=utf-8'},
    )


@app.get('/export.csv')
def export_csv():
    body = 'id,name,qty' + chr(10) + chr(10).join(','.join(row) for row in _ROWS) + chr(10)
    return Response(
        content=body,
        status_code=200,
        headers={
            'Content-Type': 'text/csv; charset=utf-8',
            'Content-Disposition': 'attachment; filename=export.csv',
        },
    )


@app.get('/ping')
def ping():
    return Response(
        content='pong',
        status_code=200,
        headers={
            'Content-Type': 'text/plain; charset=utf-8',
            'X-Service': 'inventory',
        },
    )


@app.delete('/items/{item_id}')
def delete_item(item_id: str):
    if not item_id.isdecimal():
        return Response(
            content=_FLASK_404_HTML,
            status_code=404,
            headers={'Content-Type': 'text/html; charset=utf-8'},
        )
    item_id_int = int(item_id)
    if item_id_int != 1:
        return _json_response({'error': 'item not found'}, 404)
    return Response(
        status_code=204,
        headers={'Content-Type': 'text/html; charset=utf-8'},
    )


@app.post('/items')
async def create_item(request: Request):
    content_type = request.headers.get('content-type', '')
    mimetype = content_type.split(';', 1)[0].strip().lower()
    if mimetype != 'application/json' and not mimetype.endswith('+json'):
        data = {}
    else:
        try:
            data = await request.json() or {}
        except Exception:
            data = {}

    if 'name' not in data:
        return _json_response({'error': 'name is required'}, 400)

    return _json_response(
        {'id': 9, 'name': data['name']},
        201,
        headers={'Location': '/items/9'},
    )