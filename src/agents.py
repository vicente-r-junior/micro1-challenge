"""The three specialised agents and the tools the repair agent can call.

Why three agents instead of one prompt
--------------------------------------
Each one exists because a differential run showed the previous design losing
behaviour, and each is measured separately in the changelog:

* **AnalystAgent** reads the legacy module and writes a migration brief: which
  Flask idioms are present and which of them are observable from outside. The
  migrator gets an explicit risk list instead of having to notice the risks
  while it writes code.
* **MigratorAgent** writes the FastAPI module. Its context is the source, the
  brief, the route inventory extracted by AST, and the lessons the ledger
  learned on earlier cases.
* **RepairAgent** is the only agent with tools. It is handed a behavioural diff
  and can inspect individual probes, grep the legacy source, and re-run the
  differential on a candidate before committing to it. It decides what to look
  at; the loop only bounds how long it may keep looking.

None of them is the oracle. Correctness is decided by ``parity.compare``.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from llm import LLMClient
from parity import ParityReport, compare
from probing import Route
from sandbox import run_probes
from tracing import Tracer

# Budgets. Repairs that are going to succeed converge in one to three turns;
# beyond that the agent is usually re-guessing, and each turn costs a full
# model round trip. Measured in the ablation rather than assumed.
MAX_TOOL_TURNS = 8
MAX_DIFFERENTIAL_RUNS = 3


# --------------------------------------------------------------------------- #
# Response parsing
# --------------------------------------------------------------------------- #


def describe_extraction_failure(text: str, key: str = "code") -> str:
    """Say *why* nothing usable came back, not merely that nothing did.

    "no code" and "code that does not compile" are different failures and point
    at different culprits. Reporting them as the same thing sent me looking for
    a bug in this parser when the model had in fact emitted an unterminated
    f-string.
    """
    if not text or not text.strip():
        return "the model returned an empty reply"
    reasons: list[str] = []
    for candidate in _code_candidates(text.strip(), key):
        if not candidate or not candidate.strip():
            continue
        try:
            ast.parse(candidate)
        except SyntaxError as exc:
            reasons.append(f"{exc.msg} (line {exc.lineno})")
            continue
        return "the model returned Python with no imports or no handler function"
    if reasons:
        return f"the model returned Python that does not parse: {reasons[0]}"
    return "the model reply contained no recoverable code"


def extract_code(text: str, key: str = "code") -> Optional[str]:
    """Pull a Python source string out of a model reply.

    Models drift between three shapes -- a JSON object, a JSON object wrapped in
    prose, and a fenced block -- and they sometimes emit a fourth: *almost* JSON,
    with a stray brace or quote at the end. Each candidate is therefore checked
    with ``ast.parse`` before it is accepted.

    That check matters more than it looks. An earlier version fell back to
    "if the text mentions import and def, call it code", which happily returned
    a malformed JSON blob as the migration. The sandbox then failed to import it
    and the case scored 0% -- a number that measured this parser, not the agent.
    Returning ``None`` and letting the caller retry is the honest outcome.
    """
    if not text:
        return None

    for candidate in _code_candidates(text.strip(), key):
        if _is_migrated_module(candidate):
            return candidate.strip()
    return None


def _is_migrated_module(candidate: Optional[str]) -> bool:
    """Does this text parse as Python *and* look like an application module?

    Parsing alone is not enough: `{"code": "not python"}` is a perfectly valid
    Python dict literal, so a reply that failed every real extraction path would
    still be accepted as "code" and then fail to serve a single route. Any
    migration of a Flask app has at least one import and at least one function,
    so both are required.
    """
    if not candidate or not candidate.strip():
        return False
    try:
        tree = ast.parse(candidate)
    except (SyntaxError, ValueError):
        return False
    nodes = list(ast.walk(tree))
    has_import = any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in nodes)
    has_function = any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in nodes)
    return has_import and has_function


def _code_candidates(text: str, key: str):
    """Yield every plausible reading of the reply, best-formed first."""
    cleaned = text
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    for blob in (cleaned, _embedded_json(cleaned)):
        if not blob:
            continue
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and isinstance(data.get(key), str):
            yield data[key]

    # Almost-JSON: the value is well formed even when the object around it is
    # not, so decode just the string literal that follows the key.
    yield _decode_json_string_value(cleaned, key)

    match = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    if match:
        yield match.group(1)

    yield cleaned


def _decode_json_string_value(text: str, key: str) -> Optional[str]:
    """Decode the JSON string that follows ``"key":``, ignoring the rest.

    Scans for the terminating quote while honouring backslash escapes, so a
    trailing brace or a truncated object does not lose an otherwise complete
    value.
    """
    opening = re.search(rf'"{re.escape(key)}"\s*:\s*"', text)
    if not opening:
        return None
    index = opening.end()
    escaped = False
    for position in range(index, len(text)):
        char = text[position]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            try:
                return json.loads(text[index - 1 : position + 1])
            except json.JSONDecodeError:
                return None
    return None


def _embedded_json(text: str) -> Optional[str]:
    start, end = text.find("{"), text.rfind("}")
    return text[start : end + 1] if start != -1 and end > start else None


def route_inventory(routes: list[Route]) -> str:
    lines = [f"  {','.join(r.methods):<12} {r.path}" for r in routes]
    return "\n".join(lines) if lines else "  (none found)"


# --------------------------------------------------------------------------- #
# Shared case context
# --------------------------------------------------------------------------- #


@dataclass
class CaseContext:
    case_id: str
    legacy_source: str
    routes: list[Route]
    probes: list[dict[str, Any]]
    legacy_responses: list[dict[str, Any]]
    sandbox_timeout: int = 90


# --------------------------------------------------------------------------- #
# Analyst
# --------------------------------------------------------------------------- #

ANALYST_SYSTEM = """You are a senior backend engineer preparing a Flask-to-FastAPI \
migration for a service that is already in production.

You are NOT writing the migration. You are writing the brief that another \
engineer will follow. Your only concern is externally observable behaviour: the \
HTTP status codes, the response body shapes, and the exact error payloads that \
existing clients depend on today.

For every route, identify what a careless migration would silently change. Pay \
particular attention to:
- handlers that return their own error JSON with a specific status (a migration \
  that raises HTTPException changes both the status and the body shape)
- values read with a default, or coerced leniently, where Flask tolerates input \
  that a typed FastAPI signature would reject
- response keys and their exact names
- status codes that are not the framework default

Reply with ONLY a JSON object:
{"idioms": ["..."], "risks": [{"route": "...", "risk": "...", "observable": "..."}], \
"notes": "..."}"""


class AnalystAgent:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def run(self, ctx: CaseContext) -> str:
        user = (
            f"Routes discovered by static analysis:\n{route_inventory(ctx.routes)}\n\n"
            f"Legacy Flask module:\n```python\n{ctx.legacy_source}\n```"
        )
        raw = self._llm.chat(ANALYST_SYSTEM, user, tag="analyst")
        try:
            data = json.loads(_embedded_json(raw) or raw)
        except (json.JSONDecodeError, TypeError):
            return raw.strip()

        parts: list[str] = []
        if data.get("idioms"):
            parts.append("Flask idioms present: " + "; ".join(map(str, data["idioms"])))
        for risk in data.get("risks", []) or []:
            if isinstance(risk, dict):
                parts.append(
                    f"- {risk.get('route', '?')}: {risk.get('risk', '')}"
                    + (f" (observable as: {risk['observable']})" if risk.get("observable") else "")
                )
        if data.get("notes"):
            parts.append(str(data["notes"]))
        return "\n".join(parts)


# --------------------------------------------------------------------------- #
# Migrator
# --------------------------------------------------------------------------- #

MIGRATOR_SYSTEM = """You migrate legacy Flask applications to FastAPI.

The migration is judged by replaying the same HTTP requests against the old app \
and the new one and comparing the responses. Anything a client can observe must \
be identical: status code, response body keys, and error payload shape.

Rules that follow from that:
1. Preserve every status code exactly, including non-default ones (201, 400, 404).
2. Preserve error bodies verbatim. If Flask returns {"error": "not found"} with \
   404, return exactly that -- do NOT raise HTTPException, which produces \
   {"detail": ...}. Use JSONResponse(content=..., status_code=...).
3. Preserve lenient input handling. If the Flask handler accepts a value and \
   falls back to a default, a typed FastAPI parameter that rejects it with 422 \
   is a regression. Accept the loose type and coerce inside the handler.
4. Replace request.get_json() with an explicit body read or a Pydantic model, \
   but only where doing so does not change the status returned for bad input.
5. Replace current_app / current_app.config with FastAPI dependency injection.
6. Keep every route path and HTTP method. Name the application instance `app`.
7. Use Pydantic v2. Include every import so the module runs standalone.

Return ONLY a JSON object: {"code": "<the complete Python file>"}"""


class MigratorAgent:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def run(self, ctx: CaseContext, brief: str, lessons: str) -> Optional[str]:
        blocks = [
            f"Route inventory (extracted by AST, must be preserved exactly):\n{route_inventory(ctx.routes)}",
        ]
        if brief:
            blocks.append(f"Migration brief from the analysis pass:\n{brief}")
        if lessons:
            blocks.append(lessons)
        blocks.append(f"Legacy Flask module:\n```python\n{ctx.legacy_source}\n```")
        user = "\n\n".join(blocks)

        raw = self._llm.chat(MIGRATOR_SYSTEM, user, tag="migrator")
        code = extract_code(raw)
        if code:
            return code

        # The reply did not contain a parseable module. That is a formatting
        # failure, not a migration failure, so it gets one retry with the
        # constraint restated rather than being scored as a broken migration.
        retry = (
            user
            + "\n\nYour previous reply could not be parsed. Reply with a single "
            'JSON object and nothing else: {"code": "<the complete Python file>"}. '
            "No prose, no markdown fence, no trailing text after the closing brace."
        )
        return extract_code(self._llm.chat(MIGRATOR_SYSTEM, retry, tag="migrator_retry"))


# --------------------------------------------------------------------------- #
# Tools available to the repair agent
# --------------------------------------------------------------------------- #

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_probe_detail",
            "description": (
                "Show one probe in full: the exact request sent, the response the "
                "legacy Flask app gave (the required behaviour), and the response "
                "the current candidate gave."
            ),
            "parameters": {
                "type": "object",
                "properties": {"probe_id": {"type": "string"}},
                "required": ["probe_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_legacy",
            "description": (
                "Search the legacy Flask source with a regular expression. Returns "
                "matching lines with their line numbers. Use it to check what the "
                "original handler actually does before changing the migration."
            ),
            "parameters": {
                "type": "object",
                "properties": {"pattern": {"type": "string"}},
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_differential",
            "description": (
                "Run a candidate FastAPI module against the full probe set and "
                "return the parity result and the remaining failures. Budgeted: "
                f"at most {MAX_DIFFERENTIAL_RUNS} runs per repair session."
            ),
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string", "description": "complete Python module"}},
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit",
            "description": (
                "Submit the final migrated module. Call this only after "
                "run_differential reports full parity, or after you have run out "
                "of ideas and want the best candidate recorded."
            ),
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
            },
        },
    },
]


class ToolBox:
    """Deterministic tools bound to one case. No model runs inside these."""

    def __init__(self, ctx: CaseContext, tracer: Optional[Tracer] = None) -> None:
        self.ctx = ctx
        self.tracer = tracer
        self.differential_runs = 0
        self.best_code: Optional[str] = None
        self.best_report: Optional[ParityReport] = None
        self.submitted: Optional[str] = None
        self._last_report: Optional[ParityReport] = None
        self._last_code: Optional[str] = None

    # -- helpers ------------------------------------------------------------ #

    def evaluate(self, code: str) -> ParityReport:
        result = run_probes(
            code, "fastapi", self.ctx.probes, timeout_s=self.ctx.sandbox_timeout
        )
        report = compare(
            self.ctx.probes,
            self.ctx.legacy_responses,
            result.responses,
            migrated_ok=result.ok,
            migrated_error=result.failure_reason,
        )
        self._last_report, self._last_code = report, code
        if self.best_report is None or report.parity_strict > self.best_report.parity_strict:
            self.best_code, self.best_report = code, report
        return report

    # -- tool implementations ----------------------------------------------- #

    def get_probe_detail(self, probe_id: str) -> dict[str, Any]:
        probe = next((p for p in self.ctx.probes if p["id"] == probe_id), None)
        if probe is None:
            return {"error": f"no probe named {probe_id}"}
        legacy = next((r for r in self.ctx.legacy_responses if r["probe_id"] == probe_id), None)
        diff = None
        if self._last_report:
            diff = next((d for d in self._last_report.diffs if d.probe_id == probe_id), None)
        return {
            "request": {
                "method": probe["method"],
                "path": probe["path"],
                "query": probe["query"],
                "json_body": probe["json"],
                "raw_body": probe["raw_body"],
                "kind": probe["kind"],
            },
            "legacy_response": {"status": legacy and legacy["status"], "body": legacy and (legacy["json"] if legacy["json"] is not None else legacy["text"])},
            "candidate_response": (
                {"status": diff.actual_status, "body": diff.actual_body} if diff else None
            ),
            "verdict": diff.verdict if diff else "not evaluated yet",
        }

    def search_legacy(self, pattern: str) -> dict[str, Any]:
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            return {"error": f"bad regex: {exc}"}
        hits = [
            {"line": i, "text": line}
            for i, line in enumerate(self.ctx.legacy_source.splitlines(), start=1)
            if regex.search(line)
        ]
        return {"matches": hits[:40], "truncated": len(hits) > 40}

    def run_differential(self, code: str) -> dict[str, Any]:
        if self.differential_runs >= MAX_DIFFERENTIAL_RUNS:
            return {
                "error": "differential budget exhausted",
                "advice": "call submit with your best candidate",
            }
        self.differential_runs += 1
        report = self.evaluate(code)
        return {
            "run": self.differential_runs,
            "budget_left": MAX_DIFFERENTIAL_RUNS - self.differential_runs,
            **report.summary(),
            "failures": [d.render(max_body_chars=300) for d in report.failures[:6]],
        }

    def submit(self, code: str) -> dict[str, Any]:
        self.submitted = code
        return {"accepted": True}

    def dispatch(self, name: str, arguments: str) -> dict[str, Any]:
        try:
            args = json.loads(arguments or "{}")
        except json.JSONDecodeError:
            return {"error": "arguments were not valid JSON"}
        handler: Optional[Callable[..., dict[str, Any]]] = {
            "get_probe_detail": self.get_probe_detail,
            "search_legacy": self.search_legacy,
            "run_differential": self.run_differential,
            "submit": self.submit,
        }.get(name)
        if handler is None:
            return {"error": f"unknown tool {name}"}
        if self.tracer:
            self.tracer.tool_call(name, {k: (v[:400] if isinstance(v, str) else v) for k, v in args.items()})
        try:
            result = handler(**args)
        except TypeError as exc:
            result = {"error": f"bad arguments: {exc}"}
        if self.tracer:
            self.tracer.tool_result(name, {k: v for k, v in result.items() if k != "code"})
        return result


# --------------------------------------------------------------------------- #
# Repair agent
# --------------------------------------------------------------------------- #

REPAIR_SYSTEM = """You are repairing a Flask-to-FastAPI migration that does not \
yet reproduce the legacy behaviour.

The legacy Flask response is the specification. Where the migrated app answers \
differently, the migrated app is wrong -- even when its answer looks more \
correct or more idiomatic. A client in production depends on the old answer.

You have tools. Use them:
- get_probe_detail to see exactly what was sent and what each side returned
- search_legacy to check what the original handler really does
- run_differential to test a candidate before committing to it
- submit when parity is reached or your budget is spent

Work through the failures, form a hypothesis for each, then produce a corrected \
complete module and test it. Do not guess twice at the same failure without \
looking at the probe detail first."""


@dataclass
class RepairOutcome:
    code: Optional[str]
    report: Optional[ParityReport]
    turns: int = 0
    differential_runs: int = 0
    tool_calls: list[str] = field(default_factory=list)
    stop_reason: str = ""


class RepairAgent:
    def __init__(self, llm: LLMClient, tracer: Optional[Tracer] = None) -> None:
        self._llm = llm
        self._tracer = tracer

    def run(self, ctx: CaseContext, candidate: str, report: ParityReport) -> RepairOutcome:
        box = ToolBox(ctx, self._tracer)
        box.best_code, box.best_report = candidate, report
        box._last_report, box._last_code = report, candidate

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": REPAIR_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Legacy Flask module:\n```python\n{ctx.legacy_source}\n```\n\n"
                    f"Current migrated candidate:\n```python\n{candidate}\n```\n\n"
                    f"Differential result:\n{report.feedback()}"
                ),
            },
        ]

        outcome = RepairOutcome(code=candidate, report=report)

        for turn in range(MAX_TOOL_TURNS):
            outcome.turns = turn + 1
            message = self._llm.converse(messages, TOOL_SCHEMAS, tag="repair", attempt=turn)

            if not message["tool_calls"]:
                # No tool call: treat any code in the reply as a submission.
                code = extract_code(message.get("content") or "")
                if code:
                    box.evaluate(code)
                    box.submitted = code
                    outcome.stop_reason = "code returned without a tool call"
                else:
                    outcome.stop_reason = "agent stopped without submitting"
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": message.get("content"),
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {"name": tc["name"], "arguments": tc["arguments"]},
                        }
                        for tc in message["tool_calls"]
                    ],
                }
            )

            finished = False
            for call in message["tool_calls"]:
                outcome.tool_calls.append(call["name"])
                result = box.dispatch(call["name"], call["arguments"])
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": json.dumps(result, ensure_ascii=False, default=str)[:12000],
                    }
                )
                if call["name"] == "submit":
                    finished = True
                    outcome.stop_reason = "agent submitted"
                elif call["name"] == "run_differential" and result.get("parity_strict") == 1.0:
                    # Full parity: there is nothing left to buy with more turns.
                    finished = True
                    outcome.stop_reason = "full parity reached"

            if finished:
                break
        else:
            outcome.stop_reason = f"turn budget exhausted ({MAX_TOOL_TURNS})"

        # A submitted candidate is only preferred if it was actually measured;
        # otherwise the agent could hand back an untested guess that scores worse
        # than something it already had. `evaluate` keeps `best_*` in step, so
        # reporting the best measured candidate is always safe.
        if box.submitted and box.submitted != box._last_code:
            box.evaluate(box.submitted)

        outcome.code = box.best_code or box.submitted or candidate
        outcome.report = box.best_report or report
        outcome.differential_runs = box.differential_runs
        return outcome


# --------------------------------------------------------------------------- #
# Reflector: turns confirmed failures into ledger rules
# --------------------------------------------------------------------------- #

REFLECTOR_SYSTEM = """A Flask-to-FastAPI migration was tested by replaying the same \
requests against both apps. Below are the differences that remained.

Write at most three short, general rules that would have prevented these \
specific differences in ANY Flask-to-FastAPI migration. A rule must be \
actionable while writing code and must not mention this application's route \
names or field names.

Reply with ONLY a JSON object: {"rules": ["...", "..."]}"""


class ReflectorAgent:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def run(self, report: ParityReport) -> list[str]:
        failures = report.failures
        if not failures:
            return []
        detail = "\n\n".join(d.render(max_body_chars=220) for d in failures[:8])
        raw = self._llm.chat(REFLECTOR_SYSTEM, detail, tag="reflector")
        try:
            data = json.loads(_embedded_json(raw) or raw)
        except (json.JSONDecodeError, TypeError):
            return []
        rules = data.get("rules") if isinstance(data, dict) else None
        return [str(r) for r in rules][:3] if isinstance(rules, list) else []
