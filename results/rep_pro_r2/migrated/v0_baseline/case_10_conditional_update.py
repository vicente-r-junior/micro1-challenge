'''Optimistic concurrency with a version header. Synthetic case.'''

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
import json

app = FastAPI()

_DOCS = {'d1': {'id': 'd1', 'title': 'spec', 'version': 3}}


def _etag(version: int) -> str:
    return 'W/{}{}{}'.format(chr(34), version, chr(34))


class DocUpdate(BaseModel):
    title: str = Field(min_length=1)


@app.get('/docs/{doc_id}')
async def get_doc(doc_id: str):
    doc = _DOCS.get(doc_id)
    if doc is None:
        return JSONResponse({'error': 'doc not found'}, status_code=status.HTTP_404_NOT_FOUND)
    return JSONResponse(
        doc,
        status_code=status.HTTP_200_OK,
        headers={'ETag': _etag(doc['version'])},
    )


@app.patch('/docs/{doc_id}')
async def patch_doc(doc_id: str, request: Request):
    doc = _DOCS.get(doc_id)
    if doc is None:
        return JSONResponse({'error': 'doc not found'}, status_code=status.HTTP_404_NOT_FOUND)

    if_match = request.headers.get('If-Match')
    if not if_match:
        return JSONResponse(
            {'error': 'If-Match header is required', 'code': 'PRECONDITION_REQUIRED'},
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
        )
    if if_match != _etag(doc['version']):
        return JSONResponse(
            {'error': 'version conflict', 'expected': doc['version']},
            status_code=status.HTTP_409_CONFLICT,
        )

    body = await request.body()
    data = {}
    if body:
        try:
            data = json.loads(body)
        except Exception:
            data = {}
    if not isinstance(data, dict):
        data = {}

    try:
        update = DocUpdate.model_validate(data)
    except ValidationError:
        return JSONResponse(
            {'error': 'title must be a non-empty string'},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    updated_doc = {
        'id': doc['id'],
        'title': update.title,
        'version': doc['version'] + 1,
    }
    _DOCS[doc_id] = updated_doc

    return JSONResponse(
        updated_doc,
        status_code=status.HTTP_200_OK,
        headers={'ETag': _etag(updated_doc['version'])},
    )