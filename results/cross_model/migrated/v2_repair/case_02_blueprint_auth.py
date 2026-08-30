import json

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(redirect_slashes=False)

_TOKENS = {'secret-token': {'user': 'ana', 'role': 'admin'}}
_NOTES = {1: {'id': 1, 'owner': 'ana', 'text': 'first'}}


def authenticate(request: Request):
    token = request.headers.get('X-Api-Token')
    if not token:
        raise HTTPException(
            status_code=401,
            detail={'error': 'missing token', 'code': 'AUTH_001'},
        )
    identity = _TOKENS.get(token)
    if identity is None:
        raise HTTPException(
            status_code=401,
            detail={'error': 'invalid token', 'code': 'AUTH_002'},
        )
    return identity


def _flask_not_found():
    content = '''<!doctype html>
<html lang=en>
<title>404 Not Found</title>
<h1>Not Found</h1>
<p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.</p>'''
    return HTMLResponse(content=content, status_code=404)


async def _get_json_data(request: Request):
    content_type = request.headers.get('content-type', '').lower()
    if not (content_type.startswith('application/json') or '+json' in content_type):
        return None

    raw = await request.body()
    if not raw:
        return None

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return _flask_not_found()

    # Preserve the legacy Flask auth-error payload, which FastAPI would
    # otherwise wrap as {"detail": {...}}.
    if (
        exc.status_code == 401
        and isinstance(exc.detail, dict)
        and 'error' in exc.detail
        and 'code' in exc.detail
    ):
        return JSONResponse(content=exc.detail, status_code=401)

    return JSONResponse(content={'detail': exc.detail}, status_code=exc.status_code)


@app.get('/api/v1/whoami')
def whoami(identity: dict = Depends(authenticate)):
    return {'user': identity['user'], 'role': identity['role']}


@app.get('/api/v1/notes/{note_id}')
def get_note(note_id: str, identity: dict = Depends(authenticate)):
    if note_id.startswith('+') or note_id.strip() != note_id:
        return _flask_not_found()

    try:
        nid = int(note_id)
    except ValueError:
        return _flask_not_found()

    note = _NOTES.get(nid)
    if note is None:
        return _flask_not_found()
    if note['owner'] != identity['user']:
        return JSONResponse(content={'error': 'forbidden'}, status_code=403)
    return note


@app.post('/api/v1/notes')
async def create_note(request: Request, identity: dict = Depends(authenticate)):
    data = await _get_json_data(request)
    data = data or {}
    text = data.get('text')
    if not text:
        return JSONResponse(
            content={'error': 'text is required', 'code': 'VAL_001'},
            status_code=422,
        )
    return JSONResponse(
        content={'id': 2, 'owner': identity['user'], 'text': text},
        status_code=201,
    )
