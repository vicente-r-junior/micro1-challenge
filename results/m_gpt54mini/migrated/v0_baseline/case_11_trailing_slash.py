"""Trailing-slash and redirect behaviour. Synthetic case for this benchmark.

Exercises: Flask's strict_slashes redirect, an explicitly non-strict route, and
a route that only exists with the slash. Clients follow these redirects today.
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()


@app.get("/reports/")
def list_reports():
    # Declared WITH a trailing slash: FastAPI/Starlette redirects /reports to /reports/.
    return JSONResponse({"reports": ["daily", "weekly"]})


@app.get("/status")
def status():
    # Declared WITHOUT a trailing slash: /status/ returns 404.
    return JSONResponse({"status": "up"})


@app.get("/jobs", include_in_schema=True)
@app.get("/jobs/", include_in_schema=False)
def jobs():
    return JSONResponse({"jobs": []})


@app.get("/queue/{name}")
def queue(name: str):
    return JSONResponse({"queue": name, "depth": 0})