"""Deterministic route extraction and probe synthesis.

This module is the reason the evaluation can be trusted: it never calls a model.
Routes are read out of the source with ``ast``, and the request probes are
derived from those routes by fixed rules. The same probe set is sent to the
legacy Flask app and to the migrated FastAPI app, so any difference in the
responses is a difference in behaviour, not a difference in how they were asked.

Probe kinds
-----------
happy          a valid request built from the parameters the handler reads
missing_field  a body with the required keys removed
bad_type       a body with integers where the handler indexes strings
malformed_json a syntactically invalid body with a JSON content type
absent_id      a path parameter that should not resolve to anything
wrong_method   a method the route does not declare (expect 405)
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

HTTP_METHOD_DECORATORS = {"get", "post", "put", "patch", "delete", "head", "options"}
BODY_METHODS = {"POST", "PUT", "PATCH"}

# <int:cid> / <cid> / <path:sub> in Flask; {cid} in FastAPI.
_FLASK_PARAM = re.compile(r"<(?:(?P<conv>[a-zA-Z_]+):)?(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)>")
_FASTAPI_PARAM = re.compile(r"\{(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)(?::[^}]+)?\}")

_CONVERTER_VALUES: dict[str, str] = {
    "int": "1",
    "float": "1.5",
    "uuid": "00000000-0000-4000-8000-000000000000",
    "path": "probe/sub",
    "string": "probe",
    "any": "probe",
    "": "probe",
}
_CONVERTER_ABSENT: dict[str, str] = {
    "int": "999999",
    "float": "999999.0",
    "uuid": "ffffffff-ffff-4fff-8fff-ffffffffffff",
    "path": "absent/absent",
    "string": "absent",
    "any": "absent",
    "": "absent",
}


@dataclass
class Route:
    """A single (path, methods) pair discovered in the source."""

    raw_path: str
    methods: list[str]
    func_name: str
    body_keys: list[str] = field(default_factory=list)
    query_keys: list[str] = field(default_factory=list)
    query_types: dict[str, str] = field(default_factory=dict)
    header_keys: list[str] = field(default_factory=list)
    form_keys: list[str] = field(default_factory=list)
    prefix: str = ""

    @property
    def path(self) -> str:
        joined = (self.prefix.rstrip("/") + "/" + self.raw_path.lstrip("/")) if self.prefix else self.raw_path
        return "/" + joined.lstrip("/")

    @property
    def signature(self) -> str:
        """Framework-independent identity: parameter names erased."""
        canonical = _FLASK_PARAM.sub("{}", self.path)
        canonical = _FASTAPI_PARAM.sub("{}", canonical)
        return canonical.rstrip("/") or "/"


# --------------------------------------------------------------------------- #
# Route discovery
# --------------------------------------------------------------------------- #


def _decorator_calls(node: ast.AST) -> Iterable[ast.Call]:
    for dec in getattr(node, "decorator_list", []):
        if isinstance(dec, ast.Call):
            yield dec


def _attr_name(func: ast.AST) -> Optional[str]:
    return func.attr if isinstance(func, ast.Attribute) else None


def _const_str(node: ast.AST) -> Optional[str]:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _methods_from_keywords(call: ast.Call) -> Optional[list[str]]:
    for kw in call.keywords:
        if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple, ast.Set)):
            found = [_const_str(e) for e in kw.value.elts]
            values = [m.upper() for m in found if m]
            if values:
                return values
    return None


def extract_routes(source: str) -> list[Route]:
    """Discover routes in Flask *or* FastAPI source. Never executes the code.

    A module-level ``Blueprint(url_prefix=...)`` or ``APIRouter(prefix=...)`` is
    detected and applied to every route, so a blueprint module and its migrated
    router compare on equal terms.
    """
    tree = ast.parse(source)
    prefix = extract_mount_prefix(source)
    routes: list[Route] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for call in _decorator_calls(node):
            attr = _attr_name(call.func)
            if attr is None:
                continue
            if attr == "route":
                path = _const_str(call.args[0]) if call.args else None
                if path is None:
                    continue
                methods = _methods_from_keywords(call) or ["GET"]
            elif attr in HTTP_METHOD_DECORATORS:
                path = _const_str(call.args[0]) if call.args else None
                if path is None:
                    continue
                methods = [attr.upper()]
            else:
                continue

            accessed = _extract_accessed_keys(node)
            routes.append(
                Route(
                    raw_path=path,
                    methods=sorted(set(methods)),
                    func_name=node.name,
                    body_keys=accessed["body"],
                    query_keys=accessed["query"],
                    query_types=accessed["query_types"],
                    header_keys=accessed["header"],
                    form_keys=accessed["form"],
                    prefix=prefix,
                )
            )

    reqparse_keys = _reqparse_arguments(tree)
    routes.extend(_routes_from_add_url_rule(tree, prefix))
    routes.extend(_routes_from_add_resource(tree, prefix, reqparse_keys))
    routes.sort(key=lambda r: (r.signature, ",".join(r.methods)))
    return routes


def _reqparse_arguments(tree: ast.Module) -> list[str]:
    """Collect the fields declared with Flask-RESTful's reqparse.

    ``parser.add_argument("task")`` is written once at module level and the
    handler only calls ``parser.parse_args()``, so the field names are nowhere
    near the handler body. Without this the probes for a Flask-RESTful resource
    carry an empty body and never exercise its validation at all.
    """
    keys: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
            and node.args
        ):
            name = _const_str(node.args[0])
            if name and name.isidentifier() and name not in keys:
                keys.append(name)
    return keys


def _routes_from_add_resource(
    tree: ast.Module, prefix: str, reqparse_keys: list[str]
) -> list[Route]:
    """Recover routes registered through Flask-RESTful's ``Api.add_resource``.

    ``api.add_resource(Todo, "/todos/<string:todo_id>")`` maps a Resource class
    onto one or more paths, and the class's verb methods define the allowed
    methods -- the same shape as MethodView, a different API. Flask-RESTful is
    everywhere in the legacy code this tool exists to migrate, so a decorator-
    only reader would miss most of its real targets.
    """
    classes: dict[str, ast.ClassDef] = {
        node.name: node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
    }
    routes: list[Route] = []

    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_resource"
            and node.args
            and isinstance(node.args[0], ast.Name)
        ):
            continue

        cls = classes.get(node.args[0].id)
        if cls is None:
            continue
        paths = [p for p in (_const_str(a) for a in node.args[1:]) if p]
        if not paths:
            continue

        handlers = {
            item.name.upper(): item
            for item in cls.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            and item.name in HTTP_METHOD_DECORATORS
        }
        for path in paths:
            for method, handler in sorted(handlers.items()):
                accessed = _extract_accessed_keys(handler)
                body = list(accessed["body"])
                if _calls_parse_args(handler):
                    body = [k for k in reqparse_keys if k not in body] + body
                routes.append(
                    Route(
                        raw_path=path,
                        methods=[method],
                        func_name=f"{cls.name}.{handler.name}",
                        body_keys=body,
                        query_keys=accessed["query"],
                        query_types=accessed["query_types"],
                        header_keys=accessed["header"],
                        form_keys=accessed["form"],
                        prefix=prefix,
                    )
                )
    return routes


def _calls_parse_args(func: ast.AST) -> bool:
    return any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "parse_args"
        for n in ast.walk(func)
    )


def _routes_from_add_url_rule(tree: ast.Module, prefix: str) -> list[Route]:
    """Recover routes registered imperatively rather than with a decorator.

    ``app.add_url_rule("/tasks/<int:id>", view_func=TaskAPI.as_view("task"))`` is
    invisible to a decorator reader, and a case that registers its views this way
    would silently produce zero probes -- which looks like a clean run instead of
    no run at all. Flask's MethodView derives the allowed methods from the verb
    methods defined on the class, so those are read from the class body.
    """
    classes: dict[str, ast.ClassDef] = {
        node.name: node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
    }
    routes: list[Route] = []

    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_url_rule"
            and node.args
        ):
            continue
        path = _const_str(node.args[0])
        if path is None:
            continue

        view = next((kw.value for kw in node.keywords if kw.arg == "view_func"), None)
        if view is None and len(node.args) > 2:
            view = node.args[2]

        class_name: Optional[str] = None
        if (
            isinstance(view, ast.Call)
            and isinstance(view.func, ast.Attribute)
            and view.func.attr == "as_view"
            and isinstance(view.func.value, ast.Name)
        ):
            class_name = view.func.value.id

        explicit = _methods_from_keywords(node)
        cls = classes.get(class_name) if class_name else None

        if cls is not None:
            handlers = {
                item.name.upper(): item
                for item in cls.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and item.name in HTTP_METHOD_DECORATORS
            }
            for method, handler in sorted(handlers.items()):
                if explicit and method not in explicit:
                    continue
                accessed = _extract_accessed_keys(handler)
                routes.append(
                    Route(
                        raw_path=path,
                        methods=[method],
                        func_name=f"{cls.name}.{handler.name}",
                        body_keys=accessed["body"],
                        query_keys=accessed["query"],
                        query_types=accessed["query_types"],
                        header_keys=accessed["header"],
                        form_keys=accessed["form"],
                        prefix=prefix,
                    )
                )
        elif isinstance(view, ast.Name):
            target = next(
                (
                    item
                    for item in ast.walk(tree)
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.name == view.id
                ),
                None,
            )
            accessed = (
                _extract_accessed_keys(target)
                if target
                else {"body": [], "query": [], "query_types": {}, "header": []}
            )
            routes.append(
                Route(
                    raw_path=path,
                    methods=sorted(set(explicit or ["GET"])),
                    func_name=view.id,
                    body_keys=accessed["body"],
                    query_keys=accessed["query"],
                    query_types=accessed["query_types"],
                    header_keys=accessed["header"],
                    form_keys=accessed["form"],
                    prefix=prefix,
                )
            )

    return routes


def extract_mount_prefix(source: str) -> str:
    """Best-effort mount prefix of a Blueprint (Flask) or APIRouter (FastAPI)."""
    tree = ast.parse(source)
    wanted = {"Blueprint": "url_prefix", "APIRouter": "prefix"}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        keyword = wanted.get(node.func.id)
        if keyword is None:
            continue
        for kw in node.keywords:
            if kw.arg == keyword:
                value = _const_str(kw.value)
                if value:
                    return value
    return ""


_QUERY_PROBE_VALUE = {"int": "7", "float": "7.5", "bool": "true", "str": "probe"}


def _extract_accessed_keys(func: ast.AST) -> dict[str, Any]:
    """Collect the string keys the handler reads, grouped by where they come from.

    ``request.args`` yields query keys (with their ``type=`` coercion when the
    handler declares one), ``request.headers``/``cookies``/``form`` are tracked
    separately, and everything else counts as a JSON body key. Being permissive
    about body keys is safe -- a spurious key only costs coverage -- but filing a
    header as a body key would send nonsense bodies, so the source object is
    checked explicitly rather than inferred from the key name.
    """
    found: dict[str, list[str]] = {"body": [], "query": [], "header": [], "form": [], "other": []}
    query_types: dict[str, str] = {}

    def origin(node: ast.AST) -> str:
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "request"
        ):
            return {
                "args": "query",
                "values": "query",
                "headers": "header",
                "cookies": "other",
                "form": "form",
                "files": "other",
            }.get(node.attr, "body")
        return "body"

    for node in ast.walk(func):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get":
            key = _const_str(node.args[0]) if node.args else None
            if not key:
                continue
            where = origin(node.func.value)
            found[where].append(key)
            if where == "query":
                # request.args.get("limit", type=int) tells us the probe must
                # send an integer. A type-blind probe sends "probe", Flask
                # coerces it to None and FastAPI rejects it with 422 -- a
                # difference caused by the probe, not by the migration.
                for kw in node.keywords:
                    if kw.arg == "type" and isinstance(kw.value, ast.Name):
                        query_types[key] = kw.value.id
        elif isinstance(node, ast.Subscript):
            key = _const_str(node.slice)
            if key:
                found[origin(node.value)].append(key)
        elif isinstance(node, ast.Compare) and node.ops and isinstance(node.ops[0], ast.In):
            key = _const_str(node.left)
            if key and node.comparators:
                found[origin(node.comparators[0])].append(key)

    def dedupe(values: list[str], *, identifiers_only: bool = True) -> list[str]:
        seen: list[str] = []
        for value in values:
            if value in seen or (identifiers_only and not value.isidentifier()):
                continue
            seen.append(value)
        return seen

    query = dedupe(found["query"])
    body = [k for k in dedupe(found["body"]) if k not in set(query)]
    return {
        "body": body,
        "query": query,
        "query_types": query_types,
        "header": dedupe(found["header"], identifiers_only=False),
        "form": dedupe(found["form"]),
    }


# --------------------------------------------------------------------------- #
# Probe synthesis
# --------------------------------------------------------------------------- #


def _fill_path(
    path: str, table: dict[str, str], overrides: Optional[dict[str, str]] = None
) -> str:
    """Substitute path parameters.

    ``overrides`` is the case fixture, keyed by parameter name: a resource id
    that actually exists in the app's data. Without it a probe hits
    ``/accounts/probe``, every route answers 404, and the happy path is never
    exercised at all. The converter defaults in ``table`` are the fallback.
    """
    overrides = overrides or {}

    def flask_sub(match: re.Match[str]) -> str:
        name = match.group("name")
        if name in overrides:
            return str(overrides[name])
        return table.get(match.group("conv") or "", "probe")

    def fastapi_sub(match: re.Match[str]) -> str:
        name = match.group("name")
        if name in overrides:
            return str(overrides[name])
        return table.get("", "probe")

    filled = _FLASK_PARAM.sub(flask_sub, path)
    return _FASTAPI_PARAM.sub(fastapi_sub, filled)


def _has_params(path: str) -> bool:
    return bool(_FLASK_PARAM.search(path) or _FASTAPI_PARAM.search(path))


def synthesize_probes(
    routes: list[Route],
    default_headers: Optional[dict[str, str]] = None,
    path_values: Optional[dict[str, str]] = None,
    body_values: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Build the fixed probe set. Same input routes always give the same probes.

    ``default_headers`` is the case fixture -- an auth token, an API version.
    A probe cannot guess a valid credential, so the case declares one, exactly
    as an integration test would. When a fixture exists, one extra probe per
    route is sent *without* it so the rejection path is measured as well.
    """
    headers = dict(default_headers or {})
    paths = dict(path_values or {})
    bodies = dict(body_values or {})
    probes: list[dict[str, Any]] = []

    # A path can be served by several handlers (GET /items and POST /items are
    # two Route objects). The 405 probe has to consider every method declared
    # for the path, otherwise it hits a sibling handler and tests nothing.
    methods_by_path: dict[str, set[str]] = {}
    for route in routes:
        methods_by_path.setdefault(route.signature, set()).update(route.methods)

    _emitted_405: set[str] = set()

    for index, route in enumerate(routes):
        happy_path = _fill_path(route.path, _CONVERTER_VALUES, paths)
        query = {
            key: _QUERY_PROBE_VALUE.get(route.query_types.get(key, "str"), "probe")
            for key in route.query_keys
        }

        for method in route.methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            send_body = method in BODY_METHODS or (
                method == "DELETE" and (route.body_keys or route.form_keys)
            )
            # A handler reading request.form expects application/x-www-form-
            # urlencoded. Sending it JSON makes every request fail validation,
            # so the contract records nothing but 400s and the case measures
            # nothing. The encoding is inferred from what the handler reads.
            uses_form = bool(route.form_keys)
            # A case may declare realistic values for body keys whose type or
            # domain matters (an int amount, an enum). Anything undeclared gets
            # the generic string probe.
            payload_keys = route.form_keys if uses_form else route.body_keys
            payload = (
                {key: bodies.get(key, "probe") for key in payload_keys} if send_body else None
            )
            body = None if uses_form else payload
            form = payload if uses_form else None

            probes.append(
                {
                    "id": f"r{index:02d}.{method}.happy",
                    "method": method,
                    "path": happy_path,
                    "query": query,
                    "json": body,
                    "form": form,
                    "raw_body": None,
                    "headers": headers,
                    "kind": "happy",
                    "route": route.signature,
                }
            )

            if headers:
                probes.append(
                    {
                        "id": f"r{index:02d}.{method}.unauthenticated",
                        "method": method,
                        "path": happy_path,
                        "query": query,
                        "json": body,
                        "form": form,
                        "raw_body": None,
                        "headers": {},
                        "kind": "unauthenticated",
                        "route": route.signature,
                    }
                )

            if send_body and payload_keys:
                probes.append(
                    {
                        "id": f"r{index:02d}.{method}.missing_field",
                        "method": method,
                        "path": happy_path,
                        "query": query,
                        "json": None if uses_form else {},
                        "form": {} if uses_form else None,
                        "raw_body": None,
                        "headers": headers,
                        "kind": "missing_field",
                        "route": route.signature,
                    }
                )
                probes.append(
                    {
                        "id": f"r{index:02d}.{method}.bad_type",
                        "method": method,
                        "path": happy_path,
                        "query": query,
                        "json": None if uses_form else {k: 12345 for k in payload_keys},
                        "form": {k: "12345" for k in payload_keys} if uses_form else None,
                        "raw_body": None,
                        "headers": headers,
                        "kind": "bad_type",
                        "route": route.signature,
                    }
                )
                probes.append(
                    {
                        "id": f"r{index:02d}.{method}.malformed_json",
                        "method": method,
                        "path": happy_path,
                        "query": query,
                        "json": None,
                        "form": None,
                        "raw_body": "{not json",
                        "headers": headers,
                        "kind": "malformed_json",
                        "route": route.signature,
                    }
                )

            typed_query = [k for k, t in route.query_types.items() if t in ("int", "float")]
            if typed_query:
                probes.append(
                    {
                        "id": f"r{index:02d}.{method}.bad_query_type",
                        "method": method,
                        "path": happy_path,
                        "query": {**query, **{k: "not-a-number" for k in typed_query}},
                        "json": body,
                        "form": form,
                        "raw_body": None,
                        "headers": headers,
                        "kind": "bad_query_type",
                        "route": route.signature,
                    }
                )

            if _has_params(route.path):
                probes.append(
                    {
                        "id": f"r{index:02d}.{method}.absent_id",
                        "method": method,
                        "path": _fill_path(route.path, _CONVERTER_ABSENT),
                        "query": query,
                        "json": body,
                        "form": form,
                        "raw_body": None,
                        "headers": headers,
                        "kind": "absent_id",
                        "route": route.signature,
                    }
                )

        declared = methods_by_path.get(route.signature, set(route.methods))
        unused = [m for m in ("GET", "POST", "DELETE", "PUT", "PATCH") if m not in declared]
        if unused and route.signature not in _emitted_405:
            _emitted_405.add(route.signature)
            method = unused[0]
            probes.append(
                {
                    "id": f"r{index:02d}.{method}.wrong_method",
                    "method": method,
                    "path": happy_path,
                    "query": query,
                    "json": None,
                    "raw_body": None,
                    "kind": "wrong_method",
                    "route": route.signature,
                }
            )

    probes.append(
        {
            "id": "global.GET.unknown_path",
            "method": "GET",
            "path": "/__definitely_not_a_route__",
            "query": {},
            "json": None,
            "raw_body": None,
            "headers": headers,
            "kind": "absent_id",
            "route": "__global__",
        }
    )
    return probes
