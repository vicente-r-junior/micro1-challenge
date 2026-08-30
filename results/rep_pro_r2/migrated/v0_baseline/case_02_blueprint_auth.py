"""Token-guarded blueprint, migrated to FastAPI."""
from typing import Optional

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()
api = APIRouter(prefix="/api/v1")

_TOKENS = {"secret-token": {"user": "ana", "role": "admin"}}
_NOTES = {1: {"id": 1, "owner": "ana", "text": "first"}}


class Identity(BaseModel):
    user: str
    role: str


class Note(BaseModel):
    id: int
    owner: str
    text: str


def authenticate(
    x_api_token: Optional[str] = Header(default=None, alias="X-Api-Token"),
):
    if not x_api_token:
        return JSONResponse(
            status_code=401,
            content={"error": "missing token", "code": "AUTH_001"},
        )
    identity = _TOKENS.get(x_api_token)
    if identity is None:
        return JSONResponse(
            status_code=401,
            content={"error": "invalid token", "code": "AUTH_002"},
        )
    return identity


@api.get("/whoami", response_model=Identity)
def whoami(identity: dict = Depends(authenticate)):
    return Identity(user=identity["user"], role=identity["role"])


@api.get("/notes/{note_id}", response_model=Note)
def get_note(note_id: int, identity: dict = Depends(authenticate)):
    note = _NOTES.get(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Not Found")
    if note["owner"] != identity["user"]:
        return JSONResponse(status_code=403, content={"error": "forbidden"})
    return note


@api.post("/notes", response_model=Note, status_code=201)
async def create_note(request: Request, identity: dict = Depends(authenticate)):
    data = {}
    try:
        body = await request.json()
        if isinstance(body, dict):
            data = body
    except Exception:
        pass

    text = data.get("text")
    if not text:
        return JSONResponse(
            status_code=422,
            content={"error": "text is required", "code": "VAL_001"},
        )
    return {"id": 2, "owner": identity["user"], "text": text}


app.include_router(api)