"""Token-guarded FastAPI migration."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

_TOKENS = {"secret-token": {"user": "ana", "role": "admin"}}
_NOTES = {1: {"id": 1, "owner": "ana", "text": "first"}}


class Identity(BaseModel):
    user: str
    role: str


class NoteCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: Any = None


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail,
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "text is required", "code": "VAL_001"},
    )


api = APIRouter(prefix="/api/v1")


async def get_identity(
    x_api_token: Optional[str] = Header(default=None, alias="X-Api-Token"),
) -> Identity:
    if not x_api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "missing token", "code": "AUTH_001"},
        )
    identity = _TOKENS.get(x_api_token)
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid token", "code": "AUTH_002"},
        )
    return Identity(**identity)


@api.get("/whoami")
def whoami(identity: Identity = Depends(get_identity)):
    return {"user": identity.user, "role": identity.role}


@api.get("/notes/{note_id}")
def get_note(note_id: str, identity: Identity = Depends(get_identity)):
    try:
        note_id_int = int(note_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not found"},
        )
    note = _NOTES.get(note_id_int)
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not found"},
        )
    if note["owner"] != identity.user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "forbidden"},
        )
    return note


@api.post("/notes", status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteCreate, identity: Identity = Depends(get_identity)):
    if not payload.text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "text is required", "code": "VAL_001"},
        )
    return {"id": 2, "owner": identity.user, "text": payload.text}


app.include_router(api)