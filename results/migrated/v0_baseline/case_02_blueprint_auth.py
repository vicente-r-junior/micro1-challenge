from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

_TOKENS = {"secret-token": {"user": "ana", "role": "admin"}}
_NOTES = {1: {"id": 1, "owner": "ana", "text": "first"}}


class IdentityOut(BaseModel):
    user: str
    role: str


class NoteOut(BaseModel):
    id: int
    owner: str
    text: Any


app = FastAPI()


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        content = exc.detail
    else:
        content = {"detail": exc.detail}
    return JSONResponse(status_code=exc.status_code, content=content)


def authenticate(x_api_token: Optional[str] = Header(default=None, alias="X-Api-Token")) -> Dict[str, str]:
    if not x_api_token:
        raise HTTPException(status_code=401, detail={"error": "missing token", "code": "AUTH_001"})
    identity = _TOKENS.get(x_api_token)
    if identity is None:
        raise HTTPException(status_code=401, detail={"error": "invalid token", "code": "AUTH_002"})
    return identity


@app.get("/api/v1/whoami", response_model=IdentityOut)
def whoami(identity: Dict[str, str] = Depends(authenticate)):
    return {"user": identity["user"], "role": identity["role"]}


@app.get("/api/v1/notes/{note_id}", response_model=NoteOut)
def get_note(note_id: int, identity: Dict[str, str] = Depends(authenticate)):
    note = _NOTES.get(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Not Found")
    if note["owner"] != identity["user"]:
        raise HTTPException(status_code=403, detail={"error": "forbidden"})
    return note


@app.post("/api/v1/notes", response_model=NoteOut, status_code=201)
async def create_note(request: Request, identity: Dict[str, str] = Depends(authenticate)):
    try:
        data = await request.json()
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    text = data.get("text")
    if not text:
        raise HTTPException(status_code=422, detail={"error": "text is required", "code": "VAL_001"})
    return {"id": 2, "owner": identity["user"], "text": text}