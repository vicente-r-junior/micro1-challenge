import json
from typing import Any

from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

_TOKENS = {"secret-token": {"user": "ana", "role": "admin"}}
_NOTES = {1: {"id": 1, "owner": "ana", "text": "first"}}

FLASK_404_BODY = (
    "<!doctype html>\n"
    "<html lang=en>\n"
    "<title>404 Not Found</title>\n"
    "<h1>Not Found</h1>\n"
    "<p>The requested URL was not found on the server. If you entered the URL manually "
    "please check your spelling and try again.</p>\n"
)

class FlaskJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            indent=None,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")


class AuthError(Exception):
    def __init__(self, error: str, code: str):
        super().__init__(error)
        self.error = error
        self.code = code


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.exception_handler(AuthError)
async def auth_error_handler(request: Request, exc: AuthError):
    return FlaskJSONResponse(status_code=401, content={"error": exc.error, "code": exc.code})


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return HTMLResponse(status_code=404, content=FLASK_404_BODY)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


async def require_auth(request: Request) -> dict:
    token = request.headers.get("X-Api-Token")
    if not token:
        raise AuthError("missing token", "AUTH_001")
    identity = _TOKENS.get(token)
    if identity is None:
        raise AuthError("invalid token", "AUTH_002")
    return identity


@app.post("/api/v1/notes", status_code=201)
async def create_note(request: Request, identity: dict = Depends(require_auth)):
    content_type = request.headers.get("content-type", "")
    mimetype = content_type.split(";")[0].strip().lower()
    data = {}
    if mimetype == "application/json" or mimetype.endswith("+json"):
        try:
            body = await request.json()
            if isinstance(body, dict):
                data = body
        except Exception:
            data = {}
    text = data.get("text") if isinstance(data, dict) else None
    if not text:
        return FlaskJSONResponse(status_code=422, content={"error": "text is required", "code": "VAL_001"})
    return FlaskJSONResponse(status_code=201, content={"id": 2, "owner": identity["user"], "text": text})


@app.get("/api/v1/notes/{note_id}")
async def get_note(note_id: int, identity: dict = Depends(require_auth)):
    note = _NOTES.get(note_id)
    if note is None:
        return HTMLResponse(status_code=404, content=FLASK_404_BODY)
    if note["owner"] != identity["user"]:
        return FlaskJSONResponse(status_code=403, content={"error": "forbidden"})
    return FlaskJSONResponse(content=note)


@app.get("/api/v1/whoami")
async def whoami(identity: dict = Depends(require_auth)):
    return FlaskJSONResponse(content={"user": identity["user"], "role": identity["role"]})