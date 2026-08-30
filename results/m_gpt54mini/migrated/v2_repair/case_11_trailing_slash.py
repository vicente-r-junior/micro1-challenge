"""Trailing-slash and redirect behaviour. Synthetic case for this benchmark.

Exercises: Flask's strict_slashes redirect, an explicitly non-strict route, and
a route that only exists with the slash. Clients follow these redirects today.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse

app = FastAPI()


@app.middleware("http")
async def preserve_flask_trailing_slash_behavior(request: Request, call_next):
    path = request.scope.get("path", "")
    method = request.method

    # Flask-style redirect for /reports -> /reports/ (308)
    if method == "GET" and path == "/reports":
        return RedirectResponse(url="/reports/", status_code=308)

    # Flask-style 404 for /status/ when only /status exists
    if method == "GET" and path == "/status/":
        return JSONResponse(content={"detail": "Not Found"}, status_code=404)

    response = await call_next(request)
    return response


@app.get("/reports/")
async def list_reports():
    return JSONResponse(content={"reports": ["daily", "weekly"]})


@app.get("/status")
async def status():
    return JSONResponse(content={"status": "up"})


@app.get("/jobs")
async def jobs():
    return JSONResponse(content={"jobs": []})


@app.get("/queue/{name}")
async def queue(name: str):
    return JSONResponse(content={"queue": name, "depth": 0})