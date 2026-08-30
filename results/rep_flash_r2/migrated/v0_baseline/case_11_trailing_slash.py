from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

app = FastAPI(redirect_slashes=False)


@app.get("/reports/", include_in_schema=False)
def list_reports():
    return {"reports": ["daily", "weekly"]}


@app.get("/reports", include_in_schema=False)
def reports_redirect(request: Request):
    redirect_url = "/reports/"
    if request.query_params:
        redirect_url += "?" + str(request.query_params)
    return RedirectResponse(url=redirect_url, status_code=308)


@app.get("/status")
def status():
    return {"status": "up"}


@app.get("/jobs")
def jobs():
    return {"jobs": []}


@app.get("/jobs/")
def jobs_with_slash():
    return jobs()


@app.get("/queue/{name}")
def queue(name: str):
    return {"queue": name, "depth": 0}