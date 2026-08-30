from typing import List

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

app = FastAPI(redirect_slashes=False)


class ReportsResponse(BaseModel):
    reports: List[str]


class StatusResponse(BaseModel):
    status: str


class JobsResponse(BaseModel):
    jobs: List[str]


class QueueResponse(BaseModel):
    queue: str
    depth: int


@app.get("/reports", include_in_schema=False)
async def redirect_to_reports_slash():
    return RedirectResponse(url="/reports/", status_code=308)


@app.get("/reports/", response_model=ReportsResponse)
async def list_reports():
    return {"reports": ["daily", "weekly"]}


@app.get("/status", response_model=StatusResponse)
async def status():
    return {"status": "up"}


@app.get("/jobs", response_model=JobsResponse)
@app.get("/jobs/", response_model=JobsResponse)
async def jobs():
    return {"jobs": []}


@app.get("/queue/{name}", response_model=QueueResponse)
async def queue(name: str):
    return {"queue": name, "depth": 0}