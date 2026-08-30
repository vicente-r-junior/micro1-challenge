from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

app = FastAPI()
app.state.config = {
    "PAGE_SIZE": 3,
    "FEATURE_VERBOSE": True,
    "SERVICE_NAME": "reporting",
    "MAX_RANGE_DAYS": 30,
}

_ROWS = [{"id": i, "value": i * 10} for i in range(1, 11)]


class ReportIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    days: int = 7


@app.get("/config")
def show_config() -> dict[str, Any]:
    config = app.state.config
    return {
        "service": config["SERVICE_NAME"],
        "page_size": config["PAGE_SIZE"],
        "verbose": config["FEATURE_VERBOSE"],
    }


@app.get("/rows")
def rows(size: int | None = None) -> dict[str, Any]:
    config = app.state.config
    effective_size = size or config["PAGE_SIZE"]
    page = _ROWS[:effective_size]
    payload: dict[str, Any] = {"rows": page}
    if config["FEATURE_VERBOSE"]:
        payload["meta"] = {"returned": len(page), "total": len(_ROWS)}
    return payload


@app.post("/report", status_code=status.HTTP_202_ACCEPTED)
def report(data: ReportIn) -> JSONResponse | dict[str, Any]:
    config = app.state.config
    days = data.days
    if not isinstance(days, int):
        raise HTTPException(status_code=400, detail={"error": "days must be an integer"})
    if days > config["MAX_RANGE_DAYS"]:
        raise HTTPException(
            status_code=400,
            detail={"error": "range too large", "max": config["MAX_RANGE_DAYS"]},
        )
    return {"service": config["SERVICE_NAME"], "days": days}