from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional

app = FastAPI()

class Config:
    PAGE_SIZE: int = 3
    FEATURE_VERBOSE: bool = True
    SERVICE_NAME: str = "reporting"
    MAX_RANGE_DAYS: int = 30

config = Config()

_ROWS = [{"id": i, "value": i * 10} for i in range(1, 11)]

class ConfigResponse(BaseModel):
    service: str
    page_size: int
    verbose: bool

class RowResponse(BaseModel):
    rows: List[dict]
    meta: Optional[dict] = None

class ReportRequest(BaseModel):
    days: int = Field(default=7)

@app.get("/config", response_model=ConfigResponse)
async def show_config():
    return ConfigResponse(
        service=config.SERVICE_NAME,
        page_size=config.PAGE_SIZE,
        verbose=config.FEATURE_VERBOSE,
    )

@app.get("/rows", response_model=RowResponse)
async def get_rows(size: Optional[int] = None):
    size = size or config.PAGE_SIZE
    page = _ROWS[:size]
    payload = RowResponse(rows=page)
    if config.FEATURE_VERBOSE:
        payload.meta = {"returned": len(page), "total": len(_ROWS)}
    return payload

@app.post("/report", status_code=202)
async def report(request: ReportRequest):
    days = request.days
    if not isinstance(days, int):
        raise HTTPException(status_code=400, detail="days must be an integer")
    if days > config.MAX_RANGE_DAYS:
        raise HTTPException(status_code=400, detail={"error": "range too large", "max": config.MAX_RANGE_DAYS})
    return JSONResponse(content={"service": config.SERVICE_NAME, "days": days})