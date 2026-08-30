"""Class-based views. Synthetic case for this benchmark.

Exercises: flask.views.MethodView registered with add_url_rule, shared state
between the verbs, and a 405 that Flask derives from the declared methods.
"""

from flask import Flask, jsonify, request
from flask.views import MethodView

app = Flask(__name__)

_TASKS = {1: {"id": 1, "title": "write migration", "done": False}}


class TaskAPI(MethodView):
    def get(self, task_id):
        task = _TASKS.get(task_id)
        if task is None:
            return jsonify({"error": "task not found"}), 404
        return jsonify(task)

    def put(self, task_id):
        task = _TASKS.get(task_id)
        if task is None:
            return jsonify({"error": "task not found"}), 404
        data = request.get_json(silent=True) or {}
        if "title" not in data:
            return jsonify({"error": "title is required"}), 400
        return jsonify({**task, "title": data["title"]})

    def delete(self, task_id):
        if task_id not in _TASKS:
            return jsonify({"error": "task not found"}), 404
        return jsonify({"deleted": task_id})


class TaskListAPI(MethodView):
    def get(self):
        return jsonify({"tasks": list(_TASKS.values())})

    def post(self):
        data = request.get_json(silent=True) or {}
        if "title" not in data:
            return jsonify({"error": "title is required"}), 400
        return jsonify({"id": 2, "title": data["title"], "done": False}), 201


app.add_url_rule("/tasks", view_func=TaskListAPI.as_view("tasks"))
app.add_url_rule("/tasks/<int:task_id>", view_func=TaskAPI.as_view("task"))
