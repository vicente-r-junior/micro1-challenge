from fastapi import FastAPI, Path
from pydantic import BaseModel

app = FastAPI()


@app.get("/reports/")
async def list_reports():
    # Declared WITH a trailing slash: FastAPI handles it without redirect.
    return {"reports": ["daily", "weekly"]}


@app.get("/status")
async def status():
    # Declared WITHOUT a trailing slash: FastAPI handles it correctly.
    return {"status": "up"}


@app.get("/jobs", include_in_schema=False)
async def jobs():
    return {"jobs": []}


@app.get("/queue/{name}")
async def queue(name: str = Path(...)):
    return {"queue": name, "depth": 0}