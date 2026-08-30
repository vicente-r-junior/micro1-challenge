from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class Settings(BaseModel):
    page_size: int = 3
    feature_verbose: bool = True
    service_name: str = 'reporting'
    max_range_days: int = 30


settings = Settings()


def get_settings() -> Settings:
    return settings


app = FastAPI()

_ROWS = [{'id': i, 'value': i * 10} for i in range(1, 11)]


@app.get('/config')
def show_config(config: Settings = Depends(get_settings)):
    return {
        'service': config.service_name,
        'page_size': config.page_size,
        'verbose': config.feature_verbose,
    }


@app.get('/rows')
def rows(size: Optional[str] = Query(default=None), config: Settings = Depends(get_settings)):
    if size is None:
        limit = config.page_size
    else:
        try:
            parsed = int(size)
        except (TypeError, ValueError):
            parsed = config.page_size
        limit = parsed or config.page_size

    page = _ROWS[:limit]
    payload = {'rows': page}
    if config.feature_verbose:
        payload['meta'] = {'returned': len(page), 'total': len(_ROWS)}
    return payload


@app.post('/report', status_code=202)
async def report(request: Request, config: Settings = Depends(get_settings)):
    content_type = request.headers.get('content-type', '').lower()
    if 'application/json' in content_type or '+json' in content_type:
        try:
            data = await request.json()
        except Exception:
            data = None
    else:
        data = None

    data = data or {}

    days = data.get('days', 7)
    if not isinstance(days, int):
        return JSONResponse({'error': 'days must be an integer'}, status_code=400)

    if days > config.max_range_days:
        return JSONResponse(
            {'error': 'range too large', 'max': config.max_range_days},
            status_code=400,
        )

    return {'service': config.service_name, 'days': days}


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)