import json

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class Settings(BaseModel):
    service_name: str = 'reporting'
    page_size: int = 3
    feature_verbose: bool = True
    max_range_days: int = 30


settings = Settings()


def get_settings() -> Settings:
    return settings


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

_ROWS = [{'id': i, 'value': i * 10} for i in range(1, 11)]


@app.get('/config')
async def show_config(settings: Settings = Depends(get_settings)) -> JSONResponse:
    return JSONResponse(
        content={
            'service': settings.service_name,
            'page_size': settings.page_size,
            'verbose': settings.feature_verbose,
        },
        status_code=200,
    )


@app.get('/rows')
async def rows(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    size = request.query_params.get('size')
    parsed_size = None
    if size is not None:
        try:
            parsed_size = int(size)
        except (TypeError, ValueError):
            parsed_size = None
    page_size = parsed_size or settings.page_size
    page = _ROWS[:page_size]
    payload = {'rows': page}
    if settings.feature_verbose:
        payload['meta'] = {'returned': len(page), 'total': len(_ROWS)}
    return JSONResponse(content=payload, status_code=200)


@app.post('/report')
async def report(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    raw = await request.body()
    content_type = request.headers.get('content-type', '')
    mimetype = content_type.split(';', 1)[0].strip().lower()

    parsed = None
    if mimetype == 'application/json':
        try:
            if raw:
                parsed = json.loads(raw.decode('utf-8'))
            else:
                parsed = None
        except (ValueError, UnicodeDecodeError):
            parsed = None

    data = parsed or {}
    days = data.get('days', 7)
    if not isinstance(days, int):
        return JSONResponse(
            content={'error': 'days must be an integer'},
            status_code=400,
        )
    if days > settings.max_range_days:
        return JSONResponse(
            content={'error': 'range too large', 'max': settings.max_range_days},
            status_code=400,
        )
    return JSONResponse(
        content={'service': settings.service_name, 'days': days},
        status_code=202,
    )