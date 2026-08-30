import json

from fastapi import Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class Config(BaseModel):
    PAGE_SIZE: int = 3
    FEATURE_VERBOSE: bool = True
    SERVICE_NAME: str = "reporting"
    MAX_RANGE_DAYS: int = 30


app = FastAPI()
app.state.config = Config()

_ROWS = [{"id": i, "value": i * 10} for i in range(1, 11)]


def get_config(request: Request) -> Config:
    return request.app.state.config


@app.get("/config")
def show_config(config: Config = Depends(get_config)) -> JSONResponse:
    return JSONResponse(
        {
            "service": config.SERVICE_NAME,
            "page_size": config.PAGE_SIZE,
            "verbose": config.FEATURE_VERBOSE,
        }
    )


@app.get("/rows")
async def rows(request: Request, config: Config = Depends(get_config)) -> JSONResponse:
    size_raw = request.query_params.get("size")
    try:
        size = int(size_raw) if size_raw is not None else None
    except ValueError:
        size = None
    if not size:
        size = config.PAGE_SIZE

    page = _ROWS[:size]
    payload = {"rows": page}
    if config.FEATURE_VERBOSE:
        payload["meta"] = {"returned": len(page), "total": len(_ROWS)}
    return JSONResponse(payload)


@app.post("/report")
async def report(request: Request, config: Config = Depends(get_config)) -> JSONResponse:
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    is_json = content_type == "application/json" or content_type.endswith("+json")
    data = {}
    if is_json:
        raw = await request.body()
        if raw:
            try:
                data = json.loads(raw) or {}
            except (json.JSONDecodeError, UnicodeDecodeError):
                data = {}

    days = data.get("days", 7)
    if not isinstance(days, int):
        return JSONResponse({"error": "days must be an integer"}, status_code=400)
    if days > config.MAX_RANGE_DAYS:
        return JSONResponse(
            {"error": "range too large", "max": config.MAX_RANGE_DAYS},
            status_code=400,
        )
    return JSONResponse(
        {"service": config.SERVICE_NAME, "days": days},
        status_code=status.HTTP_202_ACCEPTED,
    )