import json
from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class Identity(BaseModel):
    model_config = ConfigDict(extra='forbid')
    user: str
    role: str


class AuthError(Exception):
    def __init__(self, body):
        super().__init__()
        self.body = body


class FlaskJSONResponse(JSONResponse):
    charset = None

    def render(self, content):
        return json.dumps(
            content,
            sort_keys=True,
            separators=(',', ':'),
            ensure_ascii=False,
        ).encode('utf-8') + bytes([10])


_TOKENS = {'secret-token': {'user': 'ana', 'role': 'admin'}}
_NOTES = {1: {'id': 1, 'owner': 'ana', 'text': 'first'}}

FLASK_404_BODY = chr(10).join([
    '<!doctype html>',
    '<html lang=en>',
    '<title>404 Not Found</title>',
    '<h1>Not Found</h1>',
    '<p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.</p>',
]) + chr(10)

FLASK_405_BODY = chr(10).join([
    '<!doctype html>',
    '<html lang=en>',
    '<title>405 Method Not Allowed</title>',
    '<h1>Method Not Allowed</h1>',
    '<p>The method is not allowed for the requested URL.</p>',
]) + chr(10)


def _is_json_content_type(value):
    media_type = value.split(';', 1)[0].strip().lower()
    return media_type == 'application/json' or (
        media_type.startswith('application/') and media_type.endswith('+json')
    )


def authenticate(request: Request):
    token = request.headers.get('X-Api-Token')
    if not token:
        raise AuthError({'error': 'missing token', 'code': 'AUTH_001'})
    identity_data = _TOKENS.get(token)
    if identity_data is None:
        raise AuthError({'error': 'invalid token', 'code': 'AUTH_002'})
    request.state.identity = Identity(**identity_data)


router = APIRouter(prefix='/api/v1', dependencies=[Depends(authenticate)])


@router.get('/whoami')
def whoami(request: Request):
    identity = request.state.identity
    return FlaskJSONResponse(
        content={'user': identity.user, 'role': identity.role},
        status_code=200,
    )


@router.get('/notes/{note_id:int}')
def get_note(request: Request, note_id: int):
    note = _NOTES.get(note_id)
    if note is None:
        return HTMLResponse(content=FLASK_404_BODY, status_code=404)
    if note['owner'] != request.state.identity.user:
        return FlaskJSONResponse(content={'error': 'forbidden'}, status_code=403)
    return FlaskJSONResponse(content=note, status_code=200)


@router.post('/notes')
async def create_note(request: Request):
    identity = request.state.identity
    raw = await request.body()
    if _is_json_content_type(request.headers.get('Content-Type', '')):
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = None
        data = data or {}
    else:
        data = {}
    text = data.get('text')
    if not text:
        return FlaskJSONResponse(
            content={'error': 'text is required', 'code': 'VAL_001'},
            status_code=422,
        )
    return FlaskJSONResponse(
        content={'id': 2, 'owner': identity.user, 'text': text},
        status_code=201,
    )


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.exception_handler(AuthError)
async def auth_error_handler(request: Request, exc: AuthError):
    return FlaskJSONResponse(content=exc.body, status_code=401)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return HTMLResponse(content=FLASK_404_BODY, status_code=404)
    if exc.status_code == 405:
        return HTMLResponse(content=FLASK_405_BODY, status_code=405)
    return FlaskJSONResponse(content={'detail': exc.detail}, status_code=exc.status_code)


app.include_router(router)