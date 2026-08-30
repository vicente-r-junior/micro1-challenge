import json
from typing import Any
from uuid import UUID

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class FlaskJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return (
            json.dumps(
                content,
                ensure_ascii=True,
                sort_keys=True,
                indent=2,
                separators=(', ', ': '),
            )
            + '\n'
        ).encode('utf-8')


app = FastAPI(default_response_class=FlaskJSONResponse)

_ORGS = {'acme': {'name': 'acme', 'plan': 'pro'}}
_REPOS = {('acme', 7): {'id': 7, 'org': 'acme', 'name': 'api'}}
_FILES = {'src/main.py': 'print(\'hi\')\n'}


@app.get('/orgs/{org_slug}')
def get_org(org_slug: str):
    org = _ORGS.get(org_slug)
    if org is None:
        return FlaskJSONResponse({'error': 'org not found', 'slug': org_slug}, status_code=404)
    return FlaskJSONResponse(org)


@app.get('/orgs/{org_slug}/repos/{repo_id:int}')
def get_repo(org_slug: str, repo_id: int):
    if org_slug not in _ORGS:
        return FlaskJSONResponse({'error': 'org not found', 'slug': org_slug}, status_code=404)
    repo = _REPOS.get((org_slug, repo_id))
    if repo is None:
        return FlaskJSONResponse({'error': 'repo not found', 'id': repo_id}, status_code=404)
    return FlaskJSONResponse(repo)


@app.get('/files/{file_path:path}')
def get_file(file_path: str):
    content = _FILES.get(file_path)
    if content is None:
        return FlaskJSONResponse({'error': 'file not found', 'path': file_path}, status_code=404)
    return FlaskJSONResponse({'path': file_path, 'bytes': len(content)})


@app.get('/traces/{trace_id:uuid}')
def get_trace(trace_id: UUID):
    return FlaskJSONResponse({'trace': str(trace_id), 'found': False}, status_code=404)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    if exc.status_code == 404:
        return HTMLResponse(
            '<!doctype html>\n'
            '<html lang=en>\n'
            '<title>404 Not Found</title>\n'
            '<h1>Not Found</h1>\n'
            '<p>The requested URL was not found on the server. '
            'If you entered the URL manually please check your spelling and try again.</p>\n',
            status_code=404,
        )
    return JSONResponse({'detail': exc.detail}, status_code=exc.status_code)