'''Order lifecycle with idempotency. Synthetic case for this benchmark.

Behaviour that lives in the handler rather than in the schema, which is exactly
the kind a type-driven rewrite loses:

  * an Idempotency-Key header makes a repeated create return the *original*
    resource with 200 instead of 201, and a reused key with a different body is
    a 422 with a specific code
  * transitions are validated against a table; an illegal one is a 409 that
    lists what would have been legal
  * delete is only allowed from draft; anywhere else is 409, not 405
  * the response carries a computed field that is not stored anywhere
  * an unknown transition target is 400, while a known-but-illegal one is 409 --
    two different statuses for what looks like the same mistake
'''

from typing import Any, List, Optional

import uvicorn
from fastapi import FastAPI, Header, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

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


class OrderResponse(BaseModel):
    id: str
    state: str
    total: Any
    lines: Any
    terminal: bool


class OrderListResponse(BaseModel):
    orders: List[OrderResponse]
    count: int


@app.get('/orders/{order_id}', response_model=OrderResponse)
async def get_order(order_id: str):
    order = _ORDERS.get(order_id)
    if order is None:
        return JSONResponse(status_code=404, content={'error': 'order not found', 'id': order_id})
    return _present(order)


@app.post('/orders', response_model=OrderResponse)
async def create_order(
    request: Request,
    response: Response,
    idempotency_key: Optional[str] = Header(default=None, alias='Idempotency-Key'),
):
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not body:
        body = {}
    total = body.get('total')
    if not isinstance(total, int) or total <= 0:
        return JSONResponse(
            status_code=400,
            content={'error': 'total must be a positive integer'},
        )

    key = idempotency_key
    if key:
        seen = _IDEMPOTENCY.get(key)
        if seen is not None:
            if seen['total'] != total:
                return JSONResponse(
                    status_code=422,
                    content={
                        'error': 'idempotency key reused with a different body',
                        'code': 'IDEMPOTENCY_MISMATCH',
                    },
                )
            # Replay: the original resource, and 200 rather than 201.
            return _present(_ORDERS[seen['id']])

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

    response.status_code = 201
    response.headers['Location'] = f'/orders/{order_id}'
    return _present(order)


@app.post('/orders/{order_id}/transition', response_model=OrderResponse)
async def transition_order(request: Request, order_id: str):
    order = _ORDERS.get(order_id)
    if order is None:
        return JSONResponse(status_code=404, content={'error': 'order not found', 'id': order_id})

    try:
        body = await request.json()
    except Exception:
        body = {}
    if not body:
        body = {}
    target = body.get('to')
    if not target:
        return JSONResponse(status_code=400, content={'error': 'to is required'})
    if target not in TRANSITIONS:
        return JSONResponse(status_code=400, content={'error': 'unknown state', 'state': target})

    allowed = TRANSITIONS[order['state']]
    if target not in allowed:
        return JSONResponse(
            status_code=409,
            content={
                'error': 'illegal transition',
                'from': order['state'],
                'to': target,
                'allowed': allowed,
            },
        )

    order['state'] = target
    return _present(order)


@app.delete('/orders/{order_id}')
async def delete_order(order_id: str):
    order = _ORDERS.get(order_id)
    if order is None:
        return JSONResponse(status_code=404, content={'error': 'order not found', 'id': order_id})
    if order['state'] != 'draft':
        return JSONResponse(
            status_code=409,
            content={
                'error': 'only draft orders can be deleted',
                'state': order['state'],
                'code': 'NOT_DELETABLE',
            },
        )
    return Response(status_code=204)


@app.get('/orders', response_model=OrderListResponse)
async def list_orders(state: Optional[str] = Query(default=None)):
    rows = list(_ORDERS.values())
    if state:
        if state not in TRANSITIONS:
            return JSONResponse(status_code=400, content={'error': 'unknown state', 'state': state})
        rows = [o for o in rows if o['state'] == state]
    return {'orders': [_present(o) for o in rows], 'count': len(rows)}


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)