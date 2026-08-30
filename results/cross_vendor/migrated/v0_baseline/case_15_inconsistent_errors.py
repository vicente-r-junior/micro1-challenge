from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, constr

app = FastAPI()

_USERS = {"u1": {"id": "u1", "name": "ana", "tier": "pro"}}
_BALANCES = {"u1": 50}
DEPRECATION = "version=1; sunset=2027-01-01"

class ChargeRequest(BaseModel):
    user_id: constr(min_length=1)
    amount: int

class BatchRequest(BaseModel):
    entries: list[ChargeRequest]

@app.middleware("http")
async def add_deprecation_header(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/v1/"):
        response.headers["X-API-Deprecation"] = DEPRECATION
    return response

@app.get("/v1/users/{user_id}")
async def v1_get_user(user_id: str):
    user = _USERS.get(user_id, {})
    return JSONResponse(content=user)

@app.get("/v2/users/{user_id}")
async def v2_get_user(user_id: str):
    user = _USERS.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail={"message": "user not found"})
    return JSONResponse(content={"data": user})

@app.post("/v1/charge")
async def v1_charge(body: ChargeRequest):
    user_id = body.user_id
    amount = body.amount

    if not user_id:
        return JSONResponse(content={"ok": False, "error": "user_id required"}, status_code=200)
    if not isinstance(amount, int):
        return JSONResponse(content={"ok": False, "error": "amount must be an integer"}, status_code=200)
    balance = _BALANCES.get(user_id)
    if balance is None:
        return JSONResponse(content={"ok": False, "error": "unknown user"}, status_code=200)
    if amount > balance:
        return JSONResponse(content={"ok": False, "error": "insufficient funds"}, status_code=200)
    return JSONResponse(content={"ok": True, "remaining": balance - amount}, status_code=200)

@app.post("/v2/charge")
async def v2_charge(body: ChargeRequest):
    balance = _BALANCES.get(body.user_id)
    if balance is None:
        raise HTTPException(status_code=404, detail={"message": "unknown user"})
    if body.amount > balance:
        raise HTTPException(status_code=402, detail={"message": "insufficient funds", "balance": balance})
    return JSONResponse(content={"remaining": balance - body.amount}, status_code=200)

@app.get("/v1/ping")
async def v1_ping():
    return JSONResponse(content="pong", status_code=200)

@app.get("/v2/ping")
async def v2_ping():
    return JSONResponse(content="pong")

@app.post("/v2/batch")
async def v2_batch(body: BatchRequest):
    outcomes = []
    for index, entry in enumerate(body.entries):
        if not isinstance(entry, dict) or "user_id" not in entry:
            outcomes.append({"index": index, "ok": False, "error": "malformed entry"})
        elif entry.user_id not in _USERS:
            outcomes.append({"index": index, "ok": False, "error": "unknown user"})
        else:
            outcomes.append({"index": index, "ok": True})

    failures = sum(1 for o in outcomes if not o["ok"])
    status = 200 if failures == 0 else 207
    return JSONResponse(content={"outcomes": outcomes, "failures": failures}, status_code=status)

@app.get("/v1/config")
async def v1_config():
    return JSONResponse(content={
        "deprecation": DEPRECATION,
        "deprecated": True,
        "isDeprecated": True,
        "tiers": ["free", "pro"],
    }, status_code=200)