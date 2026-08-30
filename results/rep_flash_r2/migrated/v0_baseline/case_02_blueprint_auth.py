from typing import Optional

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

_TOKENS = {'secret-token': {'user': 'ana', 'role': 'admin'}}
_NOTES = {1: {'id': 1, 'owner': 'ana', 'text': 'first'}}


class ApiError(Exception):
    def __init__(self, status_code: int, content: dict):
        self.status_code = status_code
        self.content = content


class NoteCreate(BaseModel):
    text: Optional[str] = None


class Note(BaseModel):
    id: int
    owner: str
    text: str


app = FastAPI()
router = APIRouter(prefix='/api/v1')


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(status_code=exc.status_code, content=exc.content)


def authenticate(x_api_token: Optional[str] = Header(default=None)) -> dict:
    if not x_api_token:
        raise ApiError(401, {'error': 'missing token', 'code': 'AUTH_001'})
    identity = _TOKENS.get(x_api_token)
    if identity is None:
        raise ApiError(401, {'error': 'invalid token', 'code': 'AUTH_002'})
    return identity


@router.get('/whoami')
async def whoami(identity: dict = Depends(authenticate)):
    return {'user': identity['user'], 'role': identity['role']}


@router.get('/notes/{note_id}')
async def get_note(note_id: int, identity: dict = Depends(authenticate)):
    note = _NOTES.get(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail='Not Found')
    if note['owner'] != identity['user']:
        raise ApiError(403, {'error': 'forbidden'})
    return Note(**note)


@router.post('/notes', status_code=201)
async def create_note(payload: Optional[NoteCreate] = None, identity: dict = Depends(authenticate)):
    if payload is None:
        payload = NoteCreate()
    if not payload.text:
        raise ApiError(422, {'error': 'text is required', 'code': 'VAL_001'})
    return Note(id=2, owner=identity['user'], text=payload.text)


app.include_router(router)