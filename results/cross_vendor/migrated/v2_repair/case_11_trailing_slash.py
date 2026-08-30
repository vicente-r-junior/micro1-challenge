from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

@app.get("/reports/")
async def list_reports():
    return JSONResponse(content={"reports": ["daily", "weekly"]}, status_code=200)

@app.get("/status")
async def status():
    return JSONResponse(content={"status": "up"}, status_code=200)

@app.get("/jobs")
async def jobs():
    return JSONResponse(content={"jobs": []}, status_code=200)

@app.get("/queue/{name}")
async def queue(name: str):
    return JSONResponse(content={"queue": name, "depth": 0}, status_code=200)