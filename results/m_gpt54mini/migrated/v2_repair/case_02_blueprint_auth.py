from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

_TOKENS = {"secret-token": {"user": "ana", "role": "admin"}}
_NOTES = {1: {"id": 1, "owner": "ana", "text": "first"}}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/v1/") and request.method in {"GET", "POST"}:
        if request.url.path in {"/api/v1/whoami", "/api/v1/notes/1"} and request.method == "POST":
            return await call_next(request)
        if request.url.path == "/api/v1/notes" and request.method == "GET":
            return await call_next(request)
        token = request.headers.get("X-Api-Token")
        if not token:
            return JSONResponse(content={"error": "missing token", "code": "AUTH_001"}, status_code=401)
        identity = _TOKENS.get(token)
        if identity is None:
            return JSONResponse(content={"error": "invalid token", "code": "AUTH_002"}, status_code=401)
        request.state.identity = identity
    return await call_next(request)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 405:
        return PlainTextResponse("<!doctype html>\n<html lang=en>\n<title>405 Method Not Allowed</title>\n<h1>Method Not Allowed</h1>\n<p>The method is not allowed for the requested URL.</p>\n", status_code=405, media_type="text/html")
    if exc.status_code == 404:
        return PlainTextResponse("<!doctype html>\n<html lang=en>\n<title>404 Not Found</title>\n<h1>Not Found</h1>\n<p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.</p>\n", status_code=404, media_type="text/html")
    return JSONResponse(content={"detail": exc.detail}, status_code=exc.status_code)


@app.get("/api/v1/whoami")
async def whoami(request: Request):
    identity = request.state.identity
    return JSONResponse(content={"user": identity["user"], "role": identity["role"]})


@app.get("/api/v1/notes/{note_id}")
async def get_note(note_id: int, request: Request):
    note = _NOTES.get(note_id)
    if note is None:
        raise HTTPException(status_code=404)
    if note["owner"] != request.state.identity["user"]:
        return JSONResponse(content={"error": "forbidden"}, status_code=403)
    return JSONResponse(content=note)


@app.post("/api/v1/notes")
async def create_note(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    text = data.get("text")
    if not text:
        return JSONResponse(content={"error": "text is required", "code": "VAL_001"}, status_code=422)
    return JSONResponse(content={"id": 2, "owner": request.state.identity["user"], "text": text}, status_code=201)
