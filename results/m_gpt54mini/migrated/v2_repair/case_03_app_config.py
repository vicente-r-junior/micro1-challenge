from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from typing import Any, Dict

app = FastAPI()
app.state.config = {
    "PAGE_SIZE": 3,
    "FEATURE_VERBOSE": True,
    "SERVICE_NAME": "reporting",
    "MAX_RANGE_DAYS": 30,
}

_ROWS = [{"id": i, "value": i * 10} for i in range(1, 11)]


def get_config(request: Request) -> Dict[str, Any]:
    return request.app.state.config


@app.get("/config")
def show_config(config: Dict[str, Any] = Depends(get_config)):
    return JSONResponse(
        content={
            "service": config["SERVICE_NAME"],
            "page_size": config["PAGE_SIZE"],
            "verbose": config["FEATURE_VERBOSE"],
        }
    )


@app.get("/rows")
def rows(request: Request, config: Dict[str, Any] = Depends(get_config)):
    size_param = request.query_params.get("size")
    try:
        size = int(size_param) if size_param is not None else None
    except (TypeError, ValueError):
        size = None
    size = size or config["PAGE_SIZE"]
    page = _ROWS[:size]
    payload = {"rows": page}
    if config["FEATURE_VERBOSE"]:
        payload["meta"] = {"returned": len(page), "total": len(_ROWS)}
    return JSONResponse(content=payload)


@app.post("/report")
async def report(request: Request, config: Dict[str, Any] = Depends(get_config)):
    try:
        data = await request.json()
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    days = data.get("days", 7)
    if not isinstance(days, int):
        return JSONResponse(content={"error": "days must be an integer"}, status_code=400)
    if days > config["MAX_RANGE_DAYS"]:
        return JSONResponse(
            content={"error": "range too large", "max": config["MAX_RANGE_DAYS"]},
            status_code=400,
        )
    return JSONResponse(content={"service": config["SERVICE_NAME"], "days": days}, status_code=202)