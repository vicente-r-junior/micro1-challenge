"""FastAPI migration of the legacy Flask configuration/reporting app."""

import json
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict


class AppConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    PAGE_SIZE: int = 3
    FEATURE_VERBOSE: bool = True
    SERVICE_NAME: str = "reporting"
    MAX_RANGE_DAYS: int = 30


_CONFIG = AppConfig()

_ROWS = [{"id": i, "value": i * 10} for i in range(1, 11)]


class FlaskJSONResponse(JSONResponse):
    """Render JSON close to Flask jsonify's compact default output."""

    media_type = "application/json"

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


app = FastAPI(default_response_class=FlaskJSONResponse, redirect_slashes=False)


def get_config() -> AppConfig:
    return _CONFIG


def _is_json_mimetype(content_type: str | None) -> bool:
    if not content_type:
        return False
    mimetype = content_type.split(";", 1)[0].strip().lower()
    return mimetype == "application/json" or (
        mimetype.startswith("application/") and mimetype.endswith("+json")
    )


async def _get_json_silent(request: Request) -> Any:
    """Approximate Flask request.get_json(silent=True)."""
    if not _is_json_mimetype(request.headers.get("content-type")):
        return None

    body = await request.body()
    try:
        return json.loads(body)
    except Exception:
        return None


@app.exception_handler(Exception)
async def _flask_like_500_handler(request: Request, exc: Exception) -> HTMLResponse:
    body = (
        "<!doctype html>\n"
        "<html lang=en>\n"
        "<title>500 Internal Server Error</title>\n"
        "<h1>Internal Server Error</h1>\n"
        "<p>The server encountered an internal error and was unable to complete your request. "
        "Either the server is overloaded or there is an error in the application.</p>\n"
    )
    return HTMLResponse(content=body, status_code=500)


@app.get("/config", response_class=FlaskJSONResponse)
def show_config(config: AppConfig = Depends(get_config)) -> FlaskJSONResponse:
    return FlaskJSONResponse(
        content={
            "service": config.SERVICE_NAME,
            "page_size": config.PAGE_SIZE,
            "verbose": config.FEATURE_VERBOSE,
        }
    )


@app.get("/rows", response_class=FlaskJSONResponse)
def rows(
    request: Request,
    config: AppConfig = Depends(get_config),
) -> FlaskJSONResponse:
    raw_values = request.query_params.getlist("size")
    converted_size: int | None = None
    if raw_values:
        try:
            converted_size = int(raw_values[0])
        except (TypeError, ValueError):
            converted_size = None

    size = converted_size or config.PAGE_SIZE
    page = _ROWS[:size]
    payload: dict[str, Any] = {"rows": page}
    if config.FEATURE_VERBOSE:
        payload["meta"] = {"returned": len(page), "total": len(_ROWS)}
    return FlaskJSONResponse(content=payload)


@app.post("/report", response_class=FlaskJSONResponse)
async def report(
    request: Request,
    config: AppConfig = Depends(get_config),
) -> FlaskJSONResponse:
    data = await _get_json_silent(request) or {}
    days = data.get("days", 7)

    if not isinstance(days, int):
        return FlaskJSONResponse(
            content={"error": "days must be an integer"},
            status_code=400,
        )
    if days > config.MAX_RANGE_DAYS:
        return FlaskJSONResponse(
            content={"error": "range too large", "max": config.MAX_RANGE_DAYS},
            status_code=400,
        )
    return FlaskJSONResponse(
        content={"service": config.SERVICE_NAME, "days": days},
        status_code=202,
    )