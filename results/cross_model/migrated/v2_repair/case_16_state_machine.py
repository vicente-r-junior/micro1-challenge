import json

from fastapi import FastAPI, Request
from fastapi.responses import Response

app = FastAPI(redirect_slashes=False)

TRANSITIONS = {
    'draft': ['submitted', 'cancelled'],
    'submitted': ['approved', 'rejected', 'cancelled'],
    'approved': ['fulfilled'],
    'rejected': [],
    'cancelled': [],
    'fulfilled': [],
}
TERMINAL = {'rejected', 'cancelled', 'fulfilled'}

_ORDERS = {
    'o1': {'id': 'o1', 'state': 'draft', 'total': 30, 'lines': 2},
    'o2': {'id': 'o2', 'state': 'approved', 'total': 90, 'lines': 5},
}
_IDEMPOTENCY = {}
_NEXT = [3]


def _present(order):
    return {**order, 'terminal': order['state'] in TERMINAL}


def _json_response(data, status_code=200, headers=None):
    body = json.dumps(data, sort_keys=True, separators=(',', ':'))
    response_headers = {'content-type': 'application/json'}
    if headers:
        response_headers.update(headers)
    return Response(content=body.encode('utf-8'), status_code=status_code, headers=response_headers)


def _is_json(content_type):
    if not content_type:
        return False
    mimetype = content_type.split(';', 1)[0].strip().lower()
    return mimetype == 'application/json' or (
        mimetype.startswith('application/') and mimetype.endswith('+json')
    )


async def _read_json(request):
    if not _is_json(request.headers.get('content-type', '')):
        return {}
    try:
        return await request.json()
    except Exception:
        return {}


@app.get('/orders/{order_id}')
async def get_order(order_id: str):
    order = _ORDERS.get(order_id)
    if order is None:
        return _json_response({'error': 'order not found', 'id': order_id}, 404)
    return _json_response(_present(order))


@app.post('/orders')
async def create_order(request: Request):
    body = await _read_json(request) or {}
    total = body.get('total')
    if not isinstance(total, int) or total <= 0:
        return _json_response({'error': 'total must be a positive integer'}, 400)

    key = request.headers.get('Idempotency-Key')
    if key:
        seen = _IDEMPOTENCY.get(key)
        if seen is not None:
            if seen['total'] != total:
                return _json_response({
                    'error': 'idempotency key reused with a different body',
                    'code': 'IDEMPOTENCY_MISMATCH',
                }, 422)
            return _json_response(_present(_ORDERS[seen['id']]), 200)

    order_id = f'o{_NEXT[0]}'
    _NEXT[0] += 1
    order = {
        'id': order_id,
        'state': 'draft',
        'total': total,
        'lines': body.get('lines', 1),
    }
    _ORDERS[order_id] = order
    if key:
        _IDEMPOTENCY[key] = {'id': order_id, 'total': total}

    return _json_response(_present(order), 201, headers={'Location': f'/orders/{order_id}'})


@app.post('/orders/{order_id}/transition')
async def transition(order_id: str, request: Request):
    order = _ORDERS.get(order_id)
    if order is None:
        return _json_response({'error': 'order not found', 'id': order_id}, 404)

    body = await _read_json(request) or {}
    target = body.get('to')
    if not target:
        return _json_response({'error': 'to is required'}, 400)
    if target not in TRANSITIONS:
        return _json_response({'error': 'unknown state', 'state': target}, 400)

    allowed = TRANSITIONS[order['state']]
    if target not in allowed:
        return _json_response({
            'error': 'illegal transition',
            'from': order['state'],
            'to': target,
            'allowed': allowed,
        }, 409)

    order['state'] = target
    return _json_response(_present(order))


@app.delete('/orders/{order_id}')
async def delete_order(order_id: str):
    order = _ORDERS.get(order_id)
    if order is None:
        return _json_response({'error': 'order not found', 'id': order_id}, 404)
    if order['state'] != 'draft':
        return _json_response({
            'error': 'only draft orders can be deleted',
            'state': order['state'],
            'code': 'NOT_DELETABLE',
        }, 409)
    return Response(status_code=204)


@app.get('/orders')
async def list_orders(request: Request):
    state = request.query_params.get('state')
    rows = list(_ORDERS.values())
    if state:
        if state not in TRANSITIONS:
            return _json_response({'error': 'unknown state', 'state': state}, 400)
        rows = [o for o in rows if o['state'] == state]
    return _json_response({'orders': [_present(o) for o in rows], 'count': len(rows)})