from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict


class AppConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    PAGE_SIZE: int = 3
    FEATURE_VERBOSE: bool = True
    SERVICE_NAME: str = 'reporting'
    MAX_RANGE_DAYS: int = 30


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.state.config = AppConfig()

_ROWS = [{'id': i, 'value': i * 10} for i in range(1, 11)]


def get_config(request: Request) -> AppConfig:
    return request.app.state.config


def _coerce_int_like_flask(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_json_request(request: Request) -> bool:
    content_type = request.headers.get('content-type', '')
    mimetype = content_type.split(';', 1)[0].strip().lower()
    return mimetype == 'application/json' or (mimetype.startswith('application/') and mimetype.endswith('+json'))


@app.get('/config')
def show_config(config: AppConfig = Depends(get_config)) -> dict[str, Any]:
    return {
        'service': config.SERVICE_NAME,
        'page_size': config.PAGE_SIZE,
        'verbose': config.FEATURE_VERBOSE,
    }


@app.get('/rows')
def rows(request: Request, config: AppConfig = Depends(get_config)) -> dict[str, Any]:
    size = _coerce_int_like_flask(request.query_params.get('size')) or config.PAGE_SIZE
    page = _ROWS[:size]
    payload: dict[str, Any] = {'rows': page}
    if config.FEATURE_VERBOSE:
        payload['meta'] = {'returned': len(page), 'total': len(_ROWS)}
    return payload


@app.post('/report')
async def report(request: Request, config: AppConfig = Depends(get_config)) -> JSONResponse:
    data: Any = {}
    if _is_json_request(request):
        try:
            parsed = await request.json()
        except ValueError:
            parsed = None
        data = parsed or {}

    days = data.get('days', 7)
    if not isinstance(days, int):
        return JSONResponse({'error': 'days must be an integer'}, status_code=400)
    if days > config.MAX_RANGE_DAYS:
        return JSONResponse({'error': 'range too large', 'max': config.MAX_RANGE_DAYS}, status_code=400)
    return JSONResponse({'service': config.SERVICE_NAME, 'days': days}, status_code=202)