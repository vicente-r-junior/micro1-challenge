"""End-to-end workflow test with a scripted model.

Runs the real orchestrator, the real sandbox and the real oracle; only the model
is replaced. That is deliberate: the parts that decide correctness must be under
test without an API key, and the test doubles as proof that the repair loop
actually closes -- the scripted agent has to *use its tools* to get there.
"""

import json

import pytest

from cases import Case
from checkpoint import HumanCheckpoint
from memory import LessonLedger
from orchestrator import run_agent, run_baseline
from tracing import Tracer

LEGACY = '''
from flask import Flask, jsonify, request
app = Flask(__name__)
_DB = {1: {"id": 1, "name": "bolt"}}

@app.route("/items/<int:item_id>", methods=["GET"])
def get_item(item_id):
    item = _DB.get(item_id)
    if item is None:
        return jsonify({"error": "item not found"}), 404
    return jsonify(item)
'''

# Idiomatic FastAPI, and wrong: HTTPException returns {"detail": ...}.
BROKEN = '''
from fastapi import FastAPI, HTTPException
app = FastAPI()
_DB = {1: {"id": 1, "name": "bolt"}}

@app.get("/items/{item_id}")
def get_item(item_id: int):
    item = _DB.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return item
'''

FIXED = '''
from fastapi import FastAPI
from fastapi.responses import JSONResponse
app = FastAPI()
_DB = {1: {"id": 1, "name": "bolt"}}

@app.get("/items/{item_id}")
def get_item(item_id: int):
    item = _DB.get(item_id)
    if item is None:
        return JSONResponse({"error": "item not found"}, status_code=404)
    return item
'''


class ScriptedLLM:
    """Replays a fixed plan and records which prompts it was given."""

    def __init__(self, plan):
        self.plan = plan
        self.seen_tags: list[str] = []
        self.prompts: list[str] = []

    def chat(self, system, user, *, tag, attempt=0):
        self.seen_tags.append(tag)
        self.prompts.append(user)
        return self.plan[tag].pop(0) if isinstance(self.plan.get(tag), list) else self.plan[tag]

    def converse(self, messages, tools, *, tag, attempt=0):
        self.seen_tags.append(tag)
        return self.plan["repair_turns"].pop(0)


@pytest.fixture
def case(tmp_path):
    path = tmp_path / "case_demo"
    path.mkdir()
    app_file = path / "legacy_app.py"
    app_file.write_text(LEGACY)
    return Case("case_demo", "demo", app_file, "synthetic", "MIT", "A", "", LEGACY)


def _tracer(tmp_path, name):
    return Tracer(tmp_path / f"{name}.jsonl", {"test": True})


def test_baseline_produces_a_plausible_migration_that_silently_regresses(case, tmp_path):
    llm = ScriptedLLM({"baseline": json.dumps({"code": BROKEN})})
    result = run_baseline(case, llm, _tracer(tmp_path, "b"), tmp_path / "out")

    assert result.ok
    # It imports, it serves the route, every status code matches -- and it is
    # still wrong, because the 404 body changed shape.
    assert 0 < result.parity_strict < 1.0
    assert not result.passed


def test_agent_repairs_the_regression_using_its_tools(case, tmp_path):
    llm = ScriptedLLM(
        {
            "analyst": json.dumps({"idioms": ["jsonify with explicit status"],
                                   "risks": [{"route": "/items/<id>", "risk": "404 body shape",
                                              "observable": '{"error": ...}'}]}),
            "migrator": json.dumps({"code": BROKEN}),
            "reflector": json.dumps({"rules": []}),
            "repair_turns": [
                {"content": None, "tool_calls": [
                    {"id": "t1", "name": "get_probe_detail",
                     "arguments": json.dumps({"probe_id": "r00.GET.absent_id"})}]},
                {"content": None, "tool_calls": [
                    {"id": "t2", "name": "run_differential",
                     "arguments": json.dumps({"code": FIXED})}]},
            ],
        }
    )
    result = run_agent(
        case, llm, _tracer(tmp_path, "a"), tmp_path / "out",
        ledger=LessonLedger(tmp_path / "lessons.json", enabled=True),
        checkpoint=HumanCheckpoint("auto"),
    )

    assert result.passed, result.error
    assert result.parity_strict == 1.0
    assert "get_probe_detail" in result.tool_calls
    assert "run_differential" in result.tool_calls
    assert result.stop_reason == "full parity reached"


def test_analyst_brief_reaches_the_migrator(case, tmp_path):
    llm = ScriptedLLM({
        "analyst": json.dumps({"idioms": ["SENTINEL_IDIOM"], "risks": []}),
        "migrator": json.dumps({"code": FIXED}),
        "reflector": json.dumps({"rules": []}),
        "repair_turns": [],
    })
    run_agent(case, llm, _tracer(tmp_path, "c"), tmp_path / "out",
              ledger=LessonLedger(tmp_path / "l.json", enabled=False),
              checkpoint=HumanCheckpoint("auto"))
    migrator_prompt = llm.prompts[llm.seen_tags.index("migrator")]
    assert "SENTINEL_IDIOM" in migrator_prompt


def test_checkpoint_blocks_the_write_until_a_human_approves(case, tmp_path):
    plan = {"analyst": json.dumps({"idioms": [], "risks": []}),
            "migrator": json.dumps({"code": FIXED}),
            "reflector": json.dumps({"rules": []}), "repair_turns": []}

    denied = run_agent(case, ScriptedLLM(dict(plan)), _tracer(tmp_path, "d"), tmp_path / "no",
                       ledger=LessonLedger(tmp_path / "l2.json", enabled=False),
                       checkpoint=HumanCheckpoint("interactive", prompt_func=lambda _: "n"))
    assert denied.passed and denied.output_file is None
    assert not (tmp_path / "no" / "case_demo.py").exists()

    allowed = run_agent(case, ScriptedLLM(dict(plan)), _tracer(tmp_path, "e"), tmp_path / "yes",
                        ledger=LessonLedger(tmp_path / "l3.json", enabled=False),
                        checkpoint=HumanCheckpoint("interactive", prompt_func=lambda _: "y"))
    assert (tmp_path / "yes" / "case_demo.py").exists()
    assert allowed.output_file is not None


def test_trajectory_records_the_workflow_decisions(case, tmp_path):
    trace = tmp_path / "t.jsonl"
    llm = ScriptedLLM({
        "analyst": json.dumps({"idioms": [], "risks": []}),
        "migrator": json.dumps({"code": FIXED}),
        "reflector": json.dumps({"rules": []}), "repair_turns": [],
    })
    run_agent(case, llm, Tracer(trace, {"test": True}), tmp_path / "out",
              ledger=LessonLedger(tmp_path / "l4.json", enabled=False),
              checkpoint=HumanCheckpoint("auto"))

    events = [json.loads(line) for line in trace.read_text().splitlines()]
    kinds = [e["kind"] for e in events]
    assert kinds[0] == "run_start" and kinds[-1] == "run_end"
    # The contract recording is a tool call, and every branch the workflow takes
    # leaves a decision with its reason. LLM calls are traced by LLMClient and
    # covered in test_llm_cache.py; this scripted double bypasses it on purpose.
    assert "tool_call" in kinds and "human_checkpoint" in kinds
    reasons = [e["why"] for e in events if e["kind"] == "decision"]
    assert any("specification" in r for r in reasons)


def test_migration_never_overwrites_its_own_source(case, tmp_path):
    """Running the CLI on a module in place must not clobber the Flask original.

    The default output name is `<out_dir>/<case id>.py`, and for a user running
    `migrate.py app.py` that resolves to `./app.py` -- the input. Losing the
    legacy file is the single most destructive thing this tool could do, so the
    write is refused rather than merely renamed.
    """
    llm = ScriptedLLM({
        "analyst": json.dumps({"idioms": [], "risks": []}),
        "migrator": json.dumps({"code": FIXED}),
        "reflector": json.dumps({"rules": []}), "repair_turns": [],
    })
    with pytest.raises(ValueError, match="refusing to write"):
        run_agent(
            case, llm, _tracer(tmp_path, "clobber"), case.path.parent,
            ledger=LessonLedger(tmp_path / "l.json", enabled=False),
            checkpoint=HumanCheckpoint("auto"),
            output_path=case.path,
        )
    assert case.path.read_text() == LEGACY      # untouched
