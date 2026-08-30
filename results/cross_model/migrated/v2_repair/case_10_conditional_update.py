'''Optimistic concurrency with a version header. Synthetic case.

Exercises: a request header that drives control flow, PATCH semantics, 409 on a
version mismatch, 428 when the header is absent, and a response header echoing the
new version.
'''

import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

_DOCS = {'d1': {'id': 'd1', 'title': 'spec', 'version': 3}}


class FlaskJSONResponse(JSONResponse):
    def render(self, content):
        return json.dumps(content, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=True).encode('utf-8') + chr(10).encode()


def _json_response(data, status_code=200, headers=None):
    return FlaskJSONResponse(content=data, status_code=status_code, headers=headers)


@app.get('/docs/{doc_id}')
async def get_doc(doc_id: str):
    doc = _DOCS.get(doc_id)
    if doc is None:
        return _json_response({'error': 'doc not found'}, status_code=404)
    etag = 'W/' + chr(34) + str(doc['version']) + chr(34)
    return _json_response(doc, status_code=200, headers={'ETag': etag})


@app.patch('/docs/{doc_id}')
async def patch_doc(doc_id: str, request: Request):
    doc = _DOCS.get(doc_id)
    if doc is None:
        return _json_response({'error': 'doc not found'}, status_code=404)

    if_match = request.headers.get('If-Match')
    if not if_match:
        return _json_response({'error': 'If-Match header is required', 'code': 'PRECONDITION_REQUIRED'}, status_code=428)
    expected = 'W/' + chr(34) + str(doc['version']) + chr(34)
    if if_match != expected:
        return _json_response({'error': 'version conflict', 'expected': doc['version']}, status_code=409)

    content_type = request.headers.get('content-type', '')
    media_type = content_type.split(';', 1)[0].strip().lower()
    is_json = media_type == 'application/json' or media_type.endswith('+json')

    data = {}
    if is_json:
        raw = await request.body()
        parsed = None
        if raw:
            try:
                parsed = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError):
                parsed = None
        data = parsed or {}

    title = data.get('title')
    if not isinstance(title, str) or not title:
        return _json_response({'error': 'title must be a non-empty string'}, status_code=400)

    new_doc = {**doc, 'title': title, 'version': doc['version'] + 1}
    etag = 'W/' + chr(34) + str(new_doc['version']) + chr(34)
    return _json_response(new_doc, status_code=200, headers={'ETag': etag})