"""Nested resources with several path converters. Synthetic case.

Exercises: string, int, uuid and path converters, a route whose parameter can
contain slashes, and a sub-resource that 404s independently of its parent.
"""

from flask import Flask, jsonify

app = Flask(__name__)

_ORGS = {"acme": {"name": "acme", "plan": "pro"}}
_REPOS = {("acme", 7): {"id": 7, "org": "acme", "name": "api"}}
_FILES = {"src/main.py": "print('hi')\n"}


@app.route("/orgs/<org_slug>", methods=["GET"])
def get_org(org_slug):
    org = _ORGS.get(org_slug)
    if org is None:
        return jsonify({"error": "org not found", "slug": org_slug}), 404
    return jsonify(org)


@app.route("/orgs/<org_slug>/repos/<int:repo_id>", methods=["GET"])
def get_repo(org_slug, repo_id):
    if org_slug not in _ORGS:
        return jsonify({"error": "org not found", "slug": org_slug}), 404
    repo = _REPOS.get((org_slug, repo_id))
    if repo is None:
        return jsonify({"error": "repo not found", "id": repo_id}), 404
    return jsonify(repo)


@app.route("/files/<path:file_path>", methods=["GET"])
def get_file(file_path):
    content = _FILES.get(file_path)
    if content is None:
        return jsonify({"error": "file not found", "path": file_path}), 404
    return jsonify({"path": file_path, "bytes": len(content)})


@app.route("/traces/<uuid:trace_id>", methods=["GET"])
def get_trace(trace_id):
    return jsonify({"trace": str(trace_id), "found": False}), 404
