"""Trailing-slash and redirect behaviour migrated from Flask to FastAPI."""

from typing import List

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict

app = FastAPI(redirect_slashes=False)


class ReportsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reports: List[str]


class StatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str


class JobsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs: List[str]


class QueueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    queue: str
    depth: int


@app.get("/reports", include_in_schema=False)
def reports_redirect(request: Request) -> RedirectResponse:
    # Flask redirects /reports to /reports/ for a route declared with a trailing slash.
    target_url = request.url.replace(path=f"{request.url.path}/")
    return RedirectResponse(url=str(target_url), status_code=308)


@app.get("/reports/", response_model=ReportsResponse)
def list_reports() -> ReportsResponse:
    # Declared WITH a trailing slash: /reports redirects above; /reports/ returns JSON.
    return ReportsResponse(reports=["daily", "weekly"])


@app.get("/status", response_model=StatusResponse)
def status() -> StatusResponse:
    # Declared WITHOUT a trailing slash: /status/ remains 404 because redirect_slashes=False.
    return StatusResponse(status="up")


@app.get("/jobs", response_model=JobsResponse)
@app.get("/jobs/", response_model=JobsResponse, include_in_schema=False)
def jobs() -> JobsResponse:
    # Flask strict_slashes=False accepts both /jobs and /jobs/.
    return JobsResponse(jobs=[])


@app.get("/queue/{name}", response_model=QueueResponse)
def queue(name: str) -> QueueResponse:
    return QueueResponse(queue=name, depth=0)