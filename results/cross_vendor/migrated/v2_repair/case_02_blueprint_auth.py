from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict

app = FastAPI()

_TOKENS = {"secret-token": {"user": "ana", "role": "admin"}}
_NOTES = {1: {"id": 1, "owner": "ana", "text": "first"}}

class NoteCreate(BaseModel):
    text: str

class Identity:
    def __init__(self, user: str, role: str):
        self.user = user
        self.role = role

async def authenticate(X_Api_Token: Optional[str] = Header(None)) -> Identity:
    if not X_Api_Token:
        return JSONResponse(content={"error": "missing token", "code": "AUTH_001"}, status_code=401)
    identity = _TOKENS.get(X_Api_Token)
    if identity is None:
        return JSONResponse(content={"error": "invalid token", "code": "AUTH_002"}, status_code=401)
    return Identity(**identity)

@app.get("/api/v1/whoami")
async def whoami(identity: Identity = Depends(authenticate)):
    return {"user": identity.user, "role": identity.role}

@app.get("/api/v1/notes/{note_id}")
async def get_note(note_id: int, identity: Identity = Depends(authenticate)):
    note = _NOTES.get(note_id)
    if note is None:
        return JSONResponse(content={"error": "not found"}, status_code=404)
    if note["owner"] != identity.user:
        return JSONResponse(content={"error": "forbidden"}, status_code=403)
    return note

@app.post("/api/v1/notes")
async def create_note(note: NoteCreate, identity: Identity = Depends(authenticate)):
    if not note.text:
        return JSONResponse(content={"error": "text is required", "code": "VAL_001"}, status_code=422)
    return JSONResponse(content={"id": 2, "owner": identity.user, "text": note.text}, status_code=201)