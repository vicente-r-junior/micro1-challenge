from fastapi import FastAPI
from fastapi.responses import RedirectResponse

app = FastAPI(redirect_slashes=False)


@app.get("/reports/")
def list_reports():
    return {"reports": ["daily", "weekly"]}


@app.get("/reports")
def list_reports_no_slash():
    return RedirectResponse(url="/reports/", status_code=308)


@app.get("/status")
def status():
    return {"status": "up"}


@app.get("/jobs")
def jobs_no_slash():
    return {"jobs": []}


@app.get("/jobs/")
def jobs_with_slash():
    return {"jobs": []}


@app.get("/queue/{name}")
def queue(name: str):
    return {"queue": name, "depth": 0}