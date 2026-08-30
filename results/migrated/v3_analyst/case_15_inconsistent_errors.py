import json
from typing import Any, Optional

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

app = FastAPI()

_USERS = {'u1': {'id': 'u1', 'name': 'ana', 'tier': 'pro'}}
_BALANCES = {'u1': 50}
DEPRECATION = 'version=1; sunset=2027-01-01'


def _is_json_content_type(content_type: Optional[str]) -> bool:
    if content_type is None:
        return False
    mimetype = content_type.split(';', 1)[0].strip().lower()
    return mimetype == 'application/json' or mimetype.endswith('+json')


async def _read_json_body(request: Request) -> Any:
    if not _is_json_content_type(request.headers.get('content-type')):
        return None
    try:
        raw = await request.body()
    except Exception:
        return None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def _v1_json_response(payload: Any, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        content=payload,
        status_code=status_code,
        headers={'X-API-Deprecation': DEPRECATION},
    )


@app.get('/v1/users/{user_id}')
async def v1_get_user(user_id: str):
    user = _USERS.get(user_id, {})
    return _v1_json_response(user)


@app.get('/v2/users/{user_id}')
async def v2_get_user(user_id: str):
    user = _USERS.get(user_id)
    if user is None:
        return JSONResponse(status_code=404, content={'message': 'user not found'})
    return JSONResponse(status_code=200, content={'data': user})


@app.post('/v1/charge')
async def v1_charge(request: Request):
    body = await _read_json_body(request) or {}
    user_id = body.get('user_id')
    amount = body.get('amount')

    if not user_id:
        return _v1_json_response({'ok': False, 'error': 'user_id required'})
    if not isinstance(amount, int):
        return _v1_json_response({'ok': False, 'error': 'amount must be an integer'})
    balance = _BALANCES.get(user_id)
    if balance is None:
        return _v1_json_response({'ok': False, 'error': 'unknown user'})
    if amount > balance:
        return _v1_json_response({'ok': False, 'error': 'insufficient funds'})
    return _v1_json_response({'ok': True, 'remaining': balance - amount})


@app.post('/v2/charge')
async def v2_charge(request: Request):
    body = await _read_json_body(request) or {}
    if 'user_id' not in body:
        return JSONResponse(status_code=422, content={'message': 'user_id required', 'field': 'user_id'})
    amount = body.get('amount')
    if not isinstance(amount, int):
        return JSONResponse(status_code=422, content={'message': 'amount must be an integer', 'field': 'amount'})
    balance = _BALANCES.get(body['user_id'])
    if balance is None:
        return JSONResponse(status_code=404, content={'message': 'unknown user'})
    if amount > balance:
        return JSONResponse(status_code=402, content={'message': 'insufficient funds', 'balance': balance})
    return JSONResponse(status_code=200, content={'remaining': balance - amount})


@app.get('/v1/ping')
async def v1_ping():
    return Response(content='pong', media_type='text/html', headers={'X-API-Deprecation': DEPRECATION})


@app.get('/v2/ping')
async def v2_ping():
    return JSONResponse(content='pong')


@app.post('/v2/batch')
async def v2_batch(request: Request):
    body = await _read_json_body(request)
    if not isinstance(body, list):
        return JSONResponse(status_code=422, content={'message': 'body must be a JSON array'})

    outcomes = []
    for index, entry in enumerate(body):
        if not isinstance(entry, dict) or 'user_id' not in entry:
            outcomes.append({'index': index, 'ok': False, 'error': 'malformed entry'})
        elif entry['user_id'] not in _USERS:
            outcomes.append({'index': index, 'ok': False, 'error': 'unknown user'})
        else:
            outcomes.append({'index': index, 'ok': True})

    failures = sum(1 for o in outcomes if not o['ok'])
    status = 200 if failures == 0 else 207
    return JSONResponse(status_code=status, content={'outcomes': outcomes, 'failures': failures})


@app.get('/v1/config')
async def v1_config():
    return _v1_json_response({
        'deprecation': DEPRECATION,
        'deprecated': True,
        'isDeprecated': True,
        'tiers': ['free', 'pro'],
    })