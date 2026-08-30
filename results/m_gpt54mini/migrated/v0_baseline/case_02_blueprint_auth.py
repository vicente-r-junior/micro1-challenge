from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI()

_TOKENS = {"secret-token": {"user": "ana", "role": "admin"}}
_NOTES = {1: {"id": 1, "owner": "ana", "text": "first"}}


class NoteCreate(BaseModel):
    text: str = Field(..., min_length=1)


async def authenticate(x_api_token: str | None = Header(default=None, alias="X-Api-Token")):
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
    return identity


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/api/v1/whoami")
async def whoami(identity: dict = Depends(authenticate)):
    return {"user": identity["user"], "role": identity["role"]}


@app.get("/api/v1/notes/{note_id}")
async def get_note(note_id: int, identity: dict = Depends(authenticate)):
    note = _NOTES.get(note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    if note["owner"] != identity["user"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "forbidden"},
        )
    return note


@app.post("/api/v1/notes", status_code=status.HTTP_201_CREATED)
async def create_note(payload: NoteCreate, identity: dict = Depends(authenticate)):
    if not payload.text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "text is required", "code": "VAL_001"},
        )
    return {"id": 2, "owner": identity["user"], "text": payload.text}