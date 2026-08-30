from fastapi import FastAPI
from fastapi.responses import RedirectResponse

app = FastAPI(redirect_slashes=False)


@app.get("/reports/")
def list_reports():
    return {"reports": ["daily", "weekly"]}


@app.get("/reports", include_in_schema=False)
def reports_redirect():
    return RedirectResponse(url="/reports/", status_code=308)


@app.get("/status")
def status():
    return {"status": "up"}


@app.get("/jobs")
def jobs():
    return {"jobs": []}


@app.get("/jobs/")
def jobs_slash():
    return {"jobs": []}


@app.get("/queue/{name}")
def queue(name: str):
    return {"queue": name, "depth": 0}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)