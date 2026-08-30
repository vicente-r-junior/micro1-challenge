"""Configuration read through current_app. Synthetic case for this benchmark.

Exercises: current_app.config lookups inside handlers, a config-derived default,
and a feature flag that changes the response shape. The migration has to turn
this into dependency injection without changing what clients see.
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI()

class Config:
    PAGE_SIZE = 3
    FEATURE_VERBOSE = True
    SERVICE_NAME = "reporting"
    MAX_RANGE_DAYS = 30

_ROWS = [{"id": i, "value": i * 10} for i in range(1, 11)]

# Dependency to get the config
async def get_config():
    return Config()

@app.get("/config")
async def show_config(config: Config = Depends(get_config)):
    return {
        "service": config.SERVICE_NAME,
        "page_size": config.PAGE_SIZE,
        "verbose": config.FEATURE_VERBOSE,
    }

@app.get("/rows")
async def rows(size: Optional[str] = None, config: Config = Depends(get_config)):
    try:
        size = int(size) if size is not None else config.PAGE_SIZE
    except (ValueError, TypeError):
        size = config.PAGE_SIZE  # Fallback to default PAGE_SIZE
    page = _ROWS[:size]
    payload = {"rows": page}
    if config.FEATURE_VERBOSE:
        payload["meta"] = {"returned": len(page), "total": len(_ROWS)}
    return payload

class ReportRequest(BaseModel):
    days: Optional[int] = 7

@app.post("/report")
async def report(data: Optional[ReportRequest] = None, config: Config = Depends(get_config)):
    if data is None:
        data = ReportRequest()
    days = data.days
    if not isinstance(days, int):
        return JSONResponse(content={"error": "days must be an integer"}, status_code=400)
    if days > config.MAX_RANGE_DAYS:
        return JSONResponse(content={"error": "range too large", "max": config.MAX_RANGE_DAYS}, status_code=400)
    return JSONResponse(content={"service": config.SERVICE_NAME, "days": days}, status_code=202)