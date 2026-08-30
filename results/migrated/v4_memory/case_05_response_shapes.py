import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI()

_ROWS = [('1', 'bolt', '40'), ('2', 'nut', '12')]


@app.get('/export.csv')
def export_csv():
    body = 'id,name,qty\n' + '\n'.join(','.join(row) for row in _ROWS) + '\n'
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
    try:
        parsed_id = int(item_id)
    except (ValueError, TypeError):
        parsed_id = None
    if parsed_id != 1:
        return JSONResponse(status_code=404, content={'error': 'item not found'})
    return Response(status_code=204, headers={'Content-Type': 'text/html; charset=utf-8'})


@app.post('/items')
async def create_item(request: Request):
    data = {}
    content_type = request.headers.get('content-type', '')
    mimetype = content_type.split(';')[0].strip().lower()
    if mimetype == 'application/json' or mimetype.endswith('+json'):
        raw = await request.body()
        if raw:
            try:
                parsed = json.loads(raw)
            except (ValueError, TypeError):
                parsed = None
            if parsed:
                data = parsed
    if not isinstance(data, dict):
        data = {}
    if 'name' not in data:
        return JSONResponse(status_code=400, content={'error': 'name is required'})
    return JSONResponse(
        status_code=201,
        content={'id': 9, 'name': data['name']},
        headers={'Location': '/items/9'},
    )