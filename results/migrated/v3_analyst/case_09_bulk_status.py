from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

_KNOWN = {'a', 'b', 'c'}


def _is_json_request(request: Request) -> bool:
    content_type = request.headers.get('content-type', '')
    if not content_type:
        return False
    mimetype = content_type.split(';', 1)[0].strip().lower()
    return mimetype == 'application/json' or mimetype.endswith('+json')


@app.post('/bulk/verify')
async def bulk_verify(request: Request):
    if not _is_json_request(request):
        return JSONResponse({'error': 'body must be JSON'}, status_code=400)
    try:
        payload = await request.json()
    except (ValueError, TypeError):
        return JSONResponse({'error': 'body must be JSON'}, status_code=400)

    if payload is None:
        return JSONResponse({'error': 'body must be JSON'}, status_code=400)
    if not isinstance(payload, list):
        return JSONResponse({'error': 'body must be a JSON array'}, status_code=400)
    if not payload:
        return JSONResponse({'error': 'array must not be empty'}, status_code=400)

    results = []
    for index, key in enumerate(payload):
        if not isinstance(key, str):
            results.append({'index': index, 'status': 'invalid', 'reason': 'not a string'})
        elif key in _KNOWN:
            results.append({'index': index, 'status': 'ok'})
        else:
            results.append({'index': index, 'status': 'unknown'})

    failed = sum(1 for r in results if r['status'] != 'ok')
    status = 200 if failed == 0 else 207
    return JSONResponse({'results': results, 'failed': failed}, status_code=status)


@app.get('/bulk/limits')
async def limits():
    return JSONResponse({'max_items': 100, 'known': sorted(_KNOWN)})