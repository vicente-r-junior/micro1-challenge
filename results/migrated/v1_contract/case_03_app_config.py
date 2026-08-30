from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

class AppConfig(BaseModel):
    PAGE_SIZE: int = 3
    FEATURE_VERBOSE: bool = True
    SERVICE_NAME: str = "reporting"
    MAX_RANGE_DAYS: int = 30

_ROWS = [{"id": i, "value": i * 10} for i in range(1, 11)]

def get_config() -> AppConfig:
    return AppConfig()

def _is_json_content_type(request: Request) -> bool:
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    return content_type == "application/json" or content_type.endswith("+json")

@app.get("/config")
def show_config(config: AppConfig = Depends(get_config)):
    return JSONResponse(content={
        "service": config.SERVICE_NAME,
        "page_size": config.PAGE_SIZE,
        "verbose": config.FEATURE_VERBOSE,
    })

@app.get("/rows")
def rows(request: Request, config: AppConfig = Depends(get_config)):
    size_raw = request.query_params.get("size")
    size = None
    if size_raw is not None:
        try:
            size = int(size_raw)
        except ValueError:
            size = None
    if not size:
        size = config.PAGE_SIZE
    page = _ROWS[:size]
    payload = {"rows": page}
    if config.FEATURE_VERBOSE:
        payload["meta"] = {"returned": len(page), "total": len(_ROWS)}
    return JSONResponse(content=payload)

@app.post("/report")
async def report(request: Request, config: AppConfig = Depends(get_config)):
    data = None
    if _is_json_content_type(request):
        try:
            data = await request.json()
        except Exception:
            data = None
    if not data:
        data = {}
    days = data.get("days", 7)
    if not isinstance(days, int):
        return JSONResponse(content={"error": "days must be an integer"}, status_code=400)
    if days > config.MAX_RANGE_DAYS:
        return JSONResponse(content={"error": "range too large", "max": config.MAX_RANGE_DAYS}, status_code=400)
    return JSONResponse(content={"service": config.SERVICE_NAME, "days": days}, status_code=202)