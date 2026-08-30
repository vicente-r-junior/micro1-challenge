import json

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse


CONFIG = {
    "PAGE_SIZE": 3,
    "FEATURE_VERBOSE": True,
    "SERVICE_NAME": "reporting",
    "MAX_RANGE_DAYS": 30,
}

_ROWS = [{"id": i, "value": i * 10} for i in range(1, 11)]


class FlaskJSONResponse(JSONResponse):
    def render(self, content):
        return json.dumps(
            content,
            ensure_ascii=True,
            allow_nan=True,
            indent=None,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")


app = FastAPI(default_response_class=FlaskJSONResponse)


def get_config() -> dict:
    return CONFIG


def _is_json_content_type(content_type: str) -> bool:
    if not content_type:
        return False
    mimetype = content_type.split(";", 1)[0].strip().lower()
    return mimetype == "application/json" or mimetype.endswith("+json")


async def _read_json_silent(request: Request):
    if not _is_json_content_type(request.headers.get("content-type", "")):
        return None
    try:
        body = await request.body()
        return json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


@app.get("/config")
def show_config(config: dict = Depends(get_config)):
    return {
        "service": config["SERVICE_NAME"],
        "page_size": config["PAGE_SIZE"],
        "verbose": config["FEATURE_VERBOSE"],
    }


@app.get("/rows")
def rows(request: Request, config: dict = Depends(get_config)):
    raw_size = request.query_params.get("size")
    if raw_size is None:
        size = config["PAGE_SIZE"]
    else:
        try:
            parsed = int(raw_size)
        except ValueError:
            size = config["PAGE_SIZE"]
        else:
            size = parsed or config["PAGE_SIZE"]

    page = _ROWS[:size]
    payload = {"rows": page}
    if config["FEATURE_VERBOSE"]:
        payload["meta"] = {"returned": len(page), "total": len(_ROWS)}
    return payload


@app.post("/report")
async def report(request: Request, config: dict = Depends(get_config)):
    data = await _read_json_silent(request) or {}
    days = data.get("days", 7)
    if not isinstance(days, int):
        return FlaskJSONResponse(
            {"error": "days must be an integer"}, status_code=400
        )
    if days > config["MAX_RANGE_DAYS"]:
        return FlaskJSONResponse(
            {"error": "range too large", "max": config["MAX_RANGE_DAYS"]},
            status_code=400,
        )
    return FlaskJSONResponse(
        {"service": config["SERVICE_NAME"], "days": days}, status_code=202
    )