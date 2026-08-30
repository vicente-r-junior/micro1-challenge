from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class Settings(BaseModel):
    PAGE_SIZE: int = 3
    FEATURE_VERBOSE: bool = True
    SERVICE_NAME: str = 'reporting'
    MAX_RANGE_DAYS: int = 30


settings = Settings()


def get_settings() -> Settings:
    return settings


app = FastAPI()

_ROWS = [{'id': i, 'value': i * 10} for i in range(1, 11)]


@app.get('/config')
def show_config(current: Settings = Depends(get_settings)):
    return {
        'service': current.SERVICE_NAME,
        'page_size': current.PAGE_SIZE,
        'verbose': current.FEATURE_VERBOSE,
    }


@app.get('/rows')
def rows(request: Request, current: Settings = Depends(get_settings)):
    raw_size = request.query_params.get('size')
    try:
        size = int(raw_size) if raw_size is not None else None
    except (TypeError, ValueError):
        size = None

    size = size or current.PAGE_SIZE
    page = _ROWS[:size]
    payload = {'rows': page}
    if current.FEATURE_VERBOSE:
        payload['meta'] = {'returned': len(page), 'total': len(_ROWS)}
    return payload


@app.post('/report', status_code=202)
async def report(request: Request, current: Settings = Depends(get_settings)):
    try:
        data = await request.json()
    except Exception:
        data = None

    data = data or {}
    days = data.get('days', 7)

    if not isinstance(days, int):
        return JSONResponse(status_code=400, content={'error': 'days must be an integer'})

    if days > current.MAX_RANGE_DAYS:
        return JSONResponse(
            status_code=400,
            content={'error': 'range too large', 'max': current.MAX_RANGE_DAYS},
        )

    return JSONResponse(
        status_code=202,
        content={'service': current.SERVICE_NAME, 'days': days},
    )