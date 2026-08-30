import json
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


_TOKENS = {"secret-token": {"user": "ana", "role": "admin"}}
_NOTES = {1: {"id": 1, "owner": "ana", "text": "first"}}


class FlaskJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return (
            json.dumps(
                content,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")


FLASK_ERROR_BODIES = {
    404: "<!doctype html>\n<html lang=en>\n<title>404 Not Found</title>\n<h1>Not Found</h1>\n<p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.</p>\n",
    405: "<!doctype html>\n<html lang=en>\n<title>405 Method Not Allowed</title>\n<h1>Method Not Allowed</h1>\n<p>The method is not allowed for the requested URL.</p>\n",
    500: "<!doctype html>\n<html lang=en>\n<title>500 Internal Server Error</title>\n<h1>Internal Server Error</h1>\n<p>The server encountered an internal error and was unable to complete your request. Either the server is overloaded or there is an error in the application.</p>\n",
}


def flask_error_response(status_code: int) -> HTMLResponse:
    return HTMLResponse(
        content=FLASK_ERROR_BODIES[status_code],
        status_code=status_code,
    )


class AuthError(Exception):
    def __init__(self, content: Dict[str, str]) -> None:
        self.content = content


app = FastAPI()
app.router.redirect_slashes = False


@app.exception_handler(AuthError)
async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
    return FlaskJSONResponse(content=exc.content, status_code=401)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code in FLASK_ERROR_BODIES:
        return flask_error_response(exc.status_code)
    return flask_error_response(500)


async def authenticate(request: Request) -> Dict[str, str]:
    token = request.headers.get("X-Api-Token")
    if not token:
        raise AuthError({"error": "missing token", "code": "AUTH_001"})

    identity = _TOKENS.get(token)
    if identity is None:
        raise AuthError({"error": "invalid token", "code": "AUTH_002"})

    return identity


def is_json_mimetype(content_type: Optional[str]) -> bool:
    if not content_type:
        return False
    mimetype = content_type.split(";", 1)[0].strip().lower()
    return mimetype == "application/json" or (
        mimetype.startswith("application/") and mimetype.endswith("+json")
    )


async def get_json_silent(request: Request) -> Any:
    if not is_json_mimetype(request.headers.get("content-type")):
        return None

    body = await request.body()
    if not body:
        return None

    try:
        return json.loads(body)
    except Exception:
        return None


@app.get("/api/v1/whoami")
async def whoami(identity: Dict[str, str] = Depends(authenticate)) -> JSONResponse:
    return FlaskJSONResponse(
        content={"user": identity["user"], "role": identity["role"]}
    )


@app.get("/api/v1/notes/{note_id:int}")
async def get_note(
    note_id: int,
    identity: Dict[str, str] = Depends(authenticate),
):
    note = _NOTES.get(note_id)
    if note is None:
        return flask_error_response(404)

    if note["owner"] != identity["user"]:
        return FlaskJSONResponse(content={"error": "forbidden"}, status_code=403)

    return FlaskJSONResponse(content=note)


@app.post("/api/v1/notes")
async def create_note(
    request: Request,
    identity: Dict[str, str] = Depends(authenticate),
) -> JSONResponse:
    data = await get_json_silent(request)
    if data is None:
        data = {}

    if not hasattr(data, "get"):
        return flask_error_response(500)

    text = data.get("text")
    if not text:
        return FlaskJSONResponse(
            content={"error": "text is required", "code": "VAL_001"},
            status_code=422,
        )

    return FlaskJSONResponse(
        content={"id": 2, "owner": identity["user"], "text": text},
        status_code=201,
    )