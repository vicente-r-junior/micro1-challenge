"""FastAPI migration of the token-guarded Flask blueprint."""

from typing import Any

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict


class Identity(BaseModel):
    model_config = ConfigDict(frozen=True)

    user: str
    role: str


class Note(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    owner: str
    text: str


class AuthError(Exception):
    def __init__(self, error: str, code: str) -> None:
        self.error = error
        self.code = code


_TOKENS: dict[str, Identity] = {"secret-token": Identity(user="ana", role="admin")}
_NOTES: dict[int, Note] = {1: Note(id=1, owner="ana", text="first")}

app = FastAPI()
api = APIRouter(prefix="/api/v1")


@app.exception_handler(AuthError)
async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"error": exc.error, "code": exc.code},
    )


async def authenticate(
    request: Request,
    x_api_token: str | None = Header(default=None, alias="X-Api-Token"),
) -> Identity:
    if not x_api_token:
        raise AuthError("missing token", "AUTH_001")

    identity = _TOKENS.get(x_api_token)
    if identity is None:
        raise AuthError("invalid token", "AUTH_002")

    request.state.identity = identity
    return identity


async def get_json_silent(request: Request) -> Any:
    content_type = request.headers.get("content-type", "")
    media_type = content_type.split(";", 1)[0].strip().lower()
    is_json = media_type == "application/json" or (
        media_type.startswith("application/") and media_type.endswith("+json")
    )
    if not is_json:
        return None

    try:
        return await request.json()
    except Exception:
        return None


@api.get("/whoami")
async def whoami(identity: Identity = Depends(authenticate)) -> dict[str, str]:
    return {"user": identity.user, "role": identity.role}


@api.get("/notes/{note_id}")
async def get_note(note_id: int, identity: Identity = Depends(authenticate)) -> dict[str, Any] | JSONResponse:
    note = _NOTES.get(note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    if note.owner != identity.user:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"error": "forbidden"})

    return note.model_dump()


@api.post("/notes")
async def create_note(request: Request, identity: Identity = Depends(authenticate)) -> JSONResponse:
    parsed = await get_json_silent(request)
    data = parsed if isinstance(parsed, dict) else {}
    text = data.get("text")

    if not text:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "text is required", "code": "VAL_001"},
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"id": 2, "owner": identity.user, "text": text},
    )


app.include_router(api)