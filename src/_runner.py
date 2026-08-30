"""Sandbox entry point. Runs inside a throwaway subprocess and directory.

Reads a job file, imports the target application, replays every probe through
the framework's own test client, and writes the observed responses to an output
file. It never imports anything from the rest of this project so that a broken
generated app cannot reach back into the harness.

Usage:  python _runner.py <job.json> <out.json>
"""

from __future__ import annotations

import importlib.util
import json
import sys
import traceback
from typing import Any


def _load_module(path: str):
    spec = importlib.util.spec_from_file_location("target_app", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["target_app"] = module
    spec.loader.exec_module(module)
    return module


def _find_app(module, framework: str):
    candidate = getattr(module, "app", None)
    if candidate is not None:
        return candidate
    wanted = "Flask" if framework == "flask" else "FastAPI"
    for value in vars(module).values():
        if type(value).__name__ == wanted:
            return value
    raise AttributeError(f"no {wanted} instance named 'app' found in module")


def _body(response_text: str) -> tuple[Any, str | None]:
    try:
        return json.loads(response_text), None
    except Exception:
        return None, response_text[:2000]


def _run_flask(app, probes: list[dict]) -> list[dict]:
    app.config["PROPAGATE_EXCEPTIONS"] = False
    app.config["TESTING"] = False
    client = app.test_client()
    out = []
    for probe in probes:
        try:
            kwargs: dict[str, Any] = {
                "method": probe["method"],
                "query_string": probe.get("query") or {},
                "headers": dict(probe.get("headers") or {}),
            }
            if probe.get("raw_body") is not None:
                kwargs["data"] = probe["raw_body"]
                kwargs["content_type"] = "application/json"
            elif probe.get("form") is not None:
                kwargs["data"] = probe["form"]
            elif probe.get("json") is not None:
                kwargs["json"] = probe["json"]
            response = client.open(probe["path"], **kwargs)
            text = response.get_data(as_text=True)
            parsed, raw = _body(text)
            out.append(
                {
                    "probe_id": probe["id"],
                    "status": response.status_code,
                    "json": parsed,
                    "text": raw,
                    "content_type": response.headers.get("Content-Type", ""),
                    "error": None,
                }
            )
        except Exception:
            out.append(
                {
                    "probe_id": probe["id"],
                    "status": None,
                    "json": None,
                    "text": None,
                    "content_type": "",
                    "error": traceback.format_exc(limit=6),
                }
            )
    return out


def _run_fastapi(app, probes: list[dict]) -> list[dict]:
    from fastapi.testclient import TestClient

    client = TestClient(app, raise_server_exceptions=False)
    out = []
    for probe in probes:
        try:
            kwargs: dict[str, Any] = {
                "params": probe.get("query") or {},
                "headers": dict(probe.get("headers") or {}),
            }
            if probe.get("raw_body") is not None:
                kwargs["content"] = probe["raw_body"]
                kwargs["headers"]["content-type"] = "application/json"
            elif probe.get("form") is not None:
                kwargs["data"] = probe["form"]
            elif probe.get("json") is not None:
                kwargs["json"] = probe["json"]
            response = client.request(probe["method"], probe["path"], **kwargs)
            parsed, raw = _body(response.text)
            out.append(
                {
                    "probe_id": probe["id"],
                    "status": response.status_code,
                    "json": parsed,
                    "text": raw,
                    "content_type": response.headers.get("content-type", ""),
                    "error": None,
                }
            )
        except Exception:
            out.append(
                {
                    "probe_id": probe["id"],
                    "status": None,
                    "json": None,
                    "text": None,
                    "content_type": "",
                    "error": traceback.format_exc(limit=6),
                }
            )
    return out


def main() -> int:
    job = json.loads(open(sys.argv[1], encoding="utf-8").read())
    out_path = sys.argv[2]
    result: dict[str, Any] = {"ok": False, "responses": [], "error": None}
    try:
        module = _load_module(job["app_file"])
        app = _find_app(module, job["framework"])
        runner = _run_flask if job["framework"] == "flask" else _run_fastapi
        result["responses"] = runner(app, job["probes"])
        result["ok"] = True
    except Exception:
        result["error"] = traceback.format_exc(limit=12)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, default=str)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
