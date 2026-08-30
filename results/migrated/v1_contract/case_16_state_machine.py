'''Order lifecycle with idempotency. Synthetic case for this benchmark.

Behaviour that lives in the handler rather than in the schema, which is exactly
the kind a type-driven rewrite loses:

  * an Idempotency-Key header makes a repeated create return the original
    resource with 200 instead of 201, and a reused key with a different body is
    a 422 with a specific code
  * transitions are validated against a table; an illegal one is a 409 that
    lists what would have been legal
  * delete is only allowed from draft; anywhere else is 409, not 405
  * the response carries a computed field that is not stored anywhere
  * an unknown transition target is 400, while a known-but-illegal one is 409 --
    two different statuses for what looks like the same mistake
'''
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

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


async def _json_body(request):
    content_type = request.headers.get('content-type', '')
    mime = content_type.split(';')[0].strip().lower()
    if mime != 'application/json' and not (mime.startswith('application/') and mime.endswith('+json')):
        return None
    try:
        return json.loads(await request.body())
    except Exception:
        return None


@app.get('/orders')
async def list_orders(request: Request):
    state = request.query_params.get('state')
    rows = list(_ORDERS.values())
    if state:
        if state not in TRANSITIONS:
            return JSONResponse(content={'error': 'unknown state', 'state': state}, status_code=400)
        rows = [o for o in rows if o['state'] == state]
    return JSONResponse(content={'orders': [_present(o) for o in rows], 'count': len(rows)})


@app.post('/orders')
async def create_order(request: Request):
    body = await _json_body(request) or {}
    total = body.get('total')
    if not isinstance(total, int) or total <= 0:
        return JSONResponse(content={'error': 'total must be a positive integer'}, status_code=400)

    key = request.headers.get('Idempotency-Key')
    if key:
        seen = _IDEMPOTENCY.get(key)
        if seen is not None:
            if seen['total'] != total:
                return JSONResponse(
                    content={
                        'error': 'idempotency key reused with a different body',
                        'code': 'IDEMPOTENCY_MISMATCH',
                    },
                    status_code=422,
                )
            return JSONResponse(content=_present(_ORDERS[seen['id']]), status_code=200)

    order_id = f'o{_NEXT[0]}'
    _NEXT[0] += 1
    order = {'id': order_id, 'state': 'draft', 'total': total, 'lines': body.get('lines', 1)}
    _ORDERS[order_id] = order
    if key:
        _IDEMPOTENCY[key] = {'id': order_id, 'total': total}

    return JSONResponse(content=_present(order), status_code=201, headers={'Location': f'/orders/{order_id}'})


@app.delete('/orders/{order_id}')
async def delete_order(order_id: str):
    order = _ORDERS.get(order_id)
    if order is None:
        return JSONResponse(content={'error': 'order not found', 'id': order_id}, status_code=404)
    if order['state'] != 'draft':
        return JSONResponse(
            content={
                'error': 'only draft orders can be deleted',
                'state': order['state'],
                'code': 'NOT_DELETABLE',
            },
            status_code=409,
        )
    return Response(status_code=204)


@app.get('/orders/{order_id}')
async def get_order(order_id: str):
    order = _ORDERS.get(order_id)
    if order is None:
        return JSONResponse(content={'error': 'order not found', 'id': order_id}, status_code=404)
    return JSONResponse(content=_present(order))


@app.post('/orders/{order_id}/transition')
async def transition(order_id: str, request: Request):
    order = _ORDERS.get(order_id)
    if order is None:
        return JSONResponse(content={'error': 'order not found', 'id': order_id}, status_code=404)

    body = await _json_body(request) or {}
    target = body.get('to')
    if not target:
        return JSONResponse(content={'error': 'to is required'}, status_code=400)
    if target not in TRANSITIONS:
        return JSONResponse(content={'error': 'unknown state', 'state': target}, status_code=400)

    allowed = TRANSITIONS[order['state']]
    if target not in allowed:
        return JSONResponse(
            content={
                'error': 'illegal transition',
                'from': order['state'],
                'to': target,
                'allowed': allowed,
            },
            status_code=409,
        )

    order['state'] = target
    return JSONResponse(content=_present(order))