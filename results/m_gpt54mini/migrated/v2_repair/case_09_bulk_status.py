from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

_KNOWN = {"a", "b", "c"}


@app.post("/bulk/verify")
async def bulk_verify(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(content={"error": "body must be JSON"}, status_code=400)

    if not isinstance(payload, list):
        return JSONResponse(content={"error": "body must be a JSON array"}, status_code=400)
    if not payload:
        return JSONResponse(content={"error": "array must not be empty"}, status_code=400)

    results = []
    for index, key in enumerate(payload):
        if not isinstance(key, str):
            results.append({"index": index, "status": "invalid", "reason": "not a string"})
        elif key in _KNOWN:
            results.append({"index": index, "status": "ok"})
        else:
            results.append({"index": index, "status": "unknown"})

    failed = sum(1 for r in results if r["status"] != "ok")
    status = 200 if failed == 0 else 207
    return JSONResponse(content={"results": results, "failed": failed}, status_code=status)


@app.get("/bulk/limits")
def limits():
    return JSONResponse(content={"max_items": 100, "known": sorted(_KNOWN)})