from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

_TOKENS = {"secret-token": {"user": "ana", "role": "admin"}}
_NOTES = {1: {"id": 1, "owner": "ana", "text": "first"}}

class NoteCreate(BaseModel):
    text: str

class Identity:
    user: str
    role: str

async def authenticate(x_api_token: str | None = Header(default=None)) -> Identity:
    if not x_api_token:
        raise HTTPException(status_code=401, detail={"error": "missing token", "code": "AUTH_001"})
    identity = _TOKENS.get(x_api_token)
    if identity is None:
        raise HTTPException(status_code=401, detail={"error": "invalid token", "code": "AUTH_002"})
    return Identity(**identity)

@app.get("/api/v1/whoami")
async def whoami(identity: Identity = Depends(authenticate)):
    return {"user": identity.user, "role": identity.role}

@app.get("/api/v1/notes/{note_id}")
async def get_note(note_id: int, identity: Identity = Depends(authenticate)):
    note = _NOTES.get(note_id)
    if note is None:
        raise HTTPException(status_code=404)
    if note["owner"] != identity.user:
        raise HTTPException(status_code=403, detail={"error": "forbidden"})
    return note

@app.post("/api/v1/notes", status_code=201)
async def create_note(note: NoteCreate, identity: Identity = Depends(authenticate)):
    if not note.text:
        raise HTTPException(status_code=422, detail={"error": "text is required", "code": "VAL_001"})
    return {"id": 2, "owner": identity.user, "text": note.text}