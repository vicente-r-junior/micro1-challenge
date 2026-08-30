"""The probe generator is the specification writer; it has to be exact."""

from probing import extract_routes, synthesize_probes

FLASK = '''
from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route("/items", methods=["GET"])
def list_items():
    limit = request.args.get("limit", type=int)
    return jsonify({"limit": limit})

@app.route("/items", methods=["POST"])
def create_item():
    data = request.get_json()
    return jsonify({"name": data["name"]}), 201

@app.route("/items/<int:item_id>", methods=["GET", "DELETE"])
def item(item_id):
    return jsonify({"id": item_id})
'''

FASTAPI = '''
from fastapi import FastAPI
app = FastAPI()

@app.get("/items")
def list_items(limit: str | None = None): ...

@app.post("/items")
def create_item(): ...

@app.get("/items/{item_id}")
def get_item(item_id: int): ...

@app.delete("/items/{item_id}")
def delete_item(item_id: int): ...
'''


def test_finds_every_route_and_method():
    routes = extract_routes(FLASK)
    assert {(r.signature, tuple(r.methods)) for r in routes} == {
        ("/items", ("GET",)),
        ("/items", ("POST",)),
        ("/items/{}", ("DELETE", "GET")),
    }


def test_route_signature_is_framework_independent():
    """A Flask route and its FastAPI migration must compare as the same route."""
    flask_sigs = {r.signature for r in extract_routes(FLASK)}
    fastapi_sigs = {r.signature for r in extract_routes(FASTAPI)}
    assert flask_sigs == fastapi_sigs == {"/items", "/items/{}"}


def test_reads_body_and_query_keys_with_types():
    routes = {r.func_name: r for r in extract_routes(FLASK)}
    assert routes["create_item"].body_keys == ["name"]
    assert routes["list_items"].query_keys == ["limit"]
    # request.args.get(..., type=int) must produce an integer probe value,
    # otherwise a faithful migration is failed for the probe's own bad input.
    assert routes["list_items"].query_types == {"limit": "int"}


def test_probes_are_deterministic():
    routes = extract_routes(FLASK)
    assert synthesize_probes(routes) == synthesize_probes(routes)


def test_probe_set_covers_the_failure_kinds_that_matter():
    kinds = {p["kind"] for p in synthesize_probes(extract_routes(FLASK))}
    assert {"happy", "missing_field", "bad_type", "malformed_json", "absent_id",
            "wrong_method", "bad_query_type"} <= kinds


def test_405_probe_never_hits_a_sibling_handler():
    """GET /items and POST /items are two routes; the 405 probe must avoid both."""
    probes = synthesize_probes(extract_routes(FLASK))
    declared = {("GET", "/items"), ("POST", "/items")}
    for probe in probes:
        if probe["kind"] == "wrong_method":
            assert (probe["method"], probe["path"]) not in declared


METHODVIEW = '''
from flask import Flask, jsonify, request
from flask.views import MethodView
app = Flask(__name__)

class TaskAPI(MethodView):
    def get(self, task_id):
        return jsonify({"id": task_id})
    def put(self, task_id):
        data = request.get_json()
        return jsonify({"title": data["title"]})

def health():
    return jsonify({"ok": True})

app.add_url_rule("/tasks/<int:task_id>", view_func=TaskAPI.as_view("task"))
app.add_url_rule("/health", view_func=health, methods=["GET"])
'''


def test_finds_routes_registered_with_add_url_rule():
    """Imperative registration is invisible to a decorator reader.

    A case that registers this way would produce zero probes, and zero probes
    reads as a clean run rather than as no run at all -- the worst possible
    failure mode for a benchmark.
    """
    routes = extract_routes(METHODVIEW)
    assert {(r.signature, tuple(r.methods)) for r in routes} == {
        ("/tasks/{}", ("GET",)),
        ("/tasks/{}", ("PUT",)),
        ("/health", ("GET",)),
    }


def test_methodview_handlers_still_yield_body_keys():
    routes = {r.func_name: r for r in extract_routes(METHODVIEW)}
    assert routes["TaskAPI.put"].body_keys == ["title"]


def test_headers_are_not_mistaken_for_body_keys():
    source = '''
from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route("/x", methods=["POST"])
def handler():
    token = request.headers.get("Authorization")
    data = request.get_json()
    return jsonify({"t": token, "n": data["name"]})
'''
    route = extract_routes(source)[0]
    assert route.body_keys == ["name"]
    assert route.header_keys == ["Authorization"]


RESTFUL = '''
from flask import Flask, request
from flask_restful import reqparse, Api, Resource
app = Flask(__name__)
api = Api(app)

parser = reqparse.RequestParser()
parser.add_argument("task")

class Todo(Resource):
    def get(self, todo_id):
        return {"id": todo_id}
    def put(self, todo_id):
        args = parser.parse_args()
        return {"task": args["task"]}, 201

class Legacy(Resource):
    def post(self):
        return {"v": request.form["data"]}

api.add_resource(Todo, "/todos/<string:todo_id>")
api.add_resource(Legacy, "/legacy")
'''


def test_finds_routes_registered_with_flask_restful_add_resource():
    routes = extract_routes(RESTFUL)
    assert {(r.signature, tuple(r.methods)) for r in routes} == {
        ("/todos/{}", ("GET",)),
        ("/todos/{}", ("PUT",)),
        ("/legacy", ("POST",)),
    }


def test_reqparse_fields_reach_the_handler_that_parses_them():
    """add_argument is at module level, nowhere near the handler body."""
    routes = {r.func_name: r for r in extract_routes(RESTFUL)}
    assert routes["Todo.put"].body_keys == ["task"]
    assert routes["Todo.get"].body_keys == []


def test_a_form_handler_is_probed_with_a_form_body_not_json():
    """Sending JSON to a request.form handler makes every probe a 400."""
    routes = {r.func_name: r for r in extract_routes(RESTFUL)}
    assert routes["Legacy.post"].form_keys == ["data"]
    probe = next(
        p for p in synthesize_probes(extract_routes(RESTFUL))
        if p["route"] == "/legacy" and p["kind"] == "happy"
    )
    assert probe["form"] == {"data": "probe"}
    assert probe["json"] is None
