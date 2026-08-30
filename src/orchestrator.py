"""The agentic workflow, and the single-prompt baseline it is measured against.

Both arms receive the same case, the same model and the same evaluation. The
only difference is what happens between reading the legacy file and producing a
FastAPI module:

    baseline   one prompt -> code
    agent      contract -> analyst -> migrator -> differential -> repair loop
               -> reflection -> human checkpoint

The contract step runs before any model is called, and the differential step
runs after: the agent is wrapped in deterministic verification on both sides.
"""

from __future__ import annotations

import difflib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from agents import (
    AnalystAgent,
    describe_extraction_failure,
    CaseContext,
    MigratorAgent,
    ReflectorAgent,
    RepairAgent,
    extract_code,
)
from cases import Case
from checkpoint import HumanCheckpoint
from llm import LLMClient
from memory import LessonLedger
from parity import ParityReport, compare
from probing import extract_routes, synthesize_probes
from sandbox import run_probes
from tracing import Tracer

BASELINE_SYSTEM = (
    "You are a senior Python engineer. Migrate the Flask application the user "
    "gives you to FastAPI. Use Pydantic v2, name the application instance `app`, "
    "and include every import so the module runs standalone.\n\n"
    "Return ONLY a JSON object: {\"code\": \"<the complete Python file>\"}"
)


@dataclass
class CaseResult:
    case_id: str
    arm: str
    ok: bool
    parity_strict: float = 0.0
    parity_lenient: float = 0.0
    probes: int = 0
    matched: int = 0
    passed: bool = False
    repair_turns: int = 0
    differential_runs: int = 0
    tool_calls: list[str] = field(default_factory=list)
    lessons_added: list[str] = field(default_factory=list)
    parity_summary: dict[str, Any] = field(default_factory=dict)
    failure_details: list[str] = field(default_factory=list)
    error: Optional[str] = None
    totals: dict[str, Any] = field(default_factory=dict)
    trace: str = ""
    output_file: Optional[str] = None
    stop_reason: str = ""

    def row(self) -> dict[str, Any]:
        """Serialise for results/summary.json.

        `wall_s` is dropped here and kept in the trajectory. In a live run it is
        real information; in a replay it measures the reader's CPU, and a
        results file meant to be diffed against the committed copy must not
        carry a field that moves for a reason unrelated to the result.
        """
        data = asdict(self)
        data["totals"] = {k: v for k, v in data["totals"].items() if k != "wall_s"}
        # Relative to the trace root, so a replay that writes its trajectories
        # elsewhere still produces an identical summary. The absolute path is
        # printed by the CLI, where it is useful.
        if data.get("trace"):
            data["trace"] = "/".join(Path(data["trace"]).parts[-2:])
        return data


# --------------------------------------------------------------------------- #
# Contract recording (no model involved)
# --------------------------------------------------------------------------- #


def record_contract(case: Case, tracer: Optional[Tracer] = None, timeout_s: int = 90):
    """Execute the legacy app and capture how it answers every probe."""
    routes = extract_routes(case.source)
    probes = synthesize_probes(routes, case.probe_headers, case.path_values, case.body_values)
    if tracer:
        tracer.tool_call("record_contract", {"case": case.id, "routes": len(routes), "probes": len(probes)})
    result = run_probes(case.source, "flask", probes, timeout_s=timeout_s)
    if tracer:
        tracer.tool_result(
            "record_contract",
            {"ok": result.ok, "responses": len(result.responses), "error": result.failure_reason},
        )
    return routes, probes, result


def _evaluate(ctx: CaseContext, code: str) -> ParityReport:
    result = run_probes(code, "fastapi", ctx.probes, timeout_s=ctx.sandbox_timeout)
    return compare(
        ctx.probes,
        ctx.legacy_responses,
        result.responses,
        migrated_ok=result.ok,
        migrated_error=result.failure_reason,
    )


def unified_diff(before: str, after: str, case_id: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"{case_id}/legacy_app.py (Flask)",
            tofile=f"{case_id}/migrated_app.py (FastAPI)",
            n=2,
        )
    )


# --------------------------------------------------------------------------- #
# Baseline arm
# --------------------------------------------------------------------------- #


def run_baseline(case: Case, llm: LLMClient, tracer: Tracer, out_dir: Path) -> CaseResult:
    """One direct prompt with basic instructions. No contract, no verification."""
    routes, probes, legacy = record_contract(case, tracer)
    if not legacy.ok:
        totals = tracer.finish({"status": "legacy_unrunnable"})
        return CaseResult(case.id, "baseline", ok=False, error=f"legacy app failed to run: {legacy.failure_reason}", totals=totals, trace=str(tracer.path))

    ctx = CaseContext(case.id, case.source, routes, probes, legacy.responses)
    raw = llm.chat(BASELINE_SYSTEM, f"```python\n{case.source}\n```", tag="baseline")
    code = extract_code(raw)
    if not code:
        why = describe_extraction_failure(raw)
        totals = tracer.finish({"status": "unparseable", "reason": why})
        return CaseResult(case.id, "baseline", ok=False, error=why, probes=len(probes), totals=totals, trace=str(tracer.path))

    report = _evaluate(ctx, code)
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"{case.id}.py"
    output.write_text(code, encoding="utf-8")

    totals = tracer.finish({"status": "done", **report.summary()})
    return CaseResult(
        case.id, "baseline", ok=True,
        parity_summary=report.summary(),
        failure_details=[d.render(max_body_chars=500) for d in report.failures],
        parity_strict=report.parity_strict, parity_lenient=report.parity_lenient,
        probes=report.total, matched=report.matched, passed=report.passed,
        error=report.migrated_error, totals=totals, trace=str(tracer.path),
        output_file=str(output),
    )


# --------------------------------------------------------------------------- #
# Agent arm
# --------------------------------------------------------------------------- #


def run_agent(
    case: Case,
    llm: LLMClient,
    tracer: Tracer,
    out_dir: Path,
    *,
    ledger: LessonLedger,
    checkpoint: HumanCheckpoint,
    use_analyst: bool = True,
    use_repair: bool = True,
    output_path: Optional[Path] = None,
) -> CaseResult:
    """Run the full workflow for one case.

    ``output_path`` names the file to write on approval. It exists because the
    default, ``out_dir/<case id>.py``, resolves to the *source file itself* when
    a user runs the CLI on a module in place -- the migration would overwrite
    the Flask original it was generated from.
    """
    routes, probes, legacy = record_contract(case, tracer)
    if not legacy.ok:
        totals = tracer.finish({"status": "legacy_unrunnable"})
        return CaseResult(case.id, "agent", ok=False, error=f"legacy app failed to run: {legacy.failure_reason}", totals=totals, trace=str(tracer.path))

    ctx = CaseContext(case.id, case.source, routes, probes, legacy.responses)
    tracer.decision(
        "contract recorded",
        "the legacy app's own responses are the specification the migration must reproduce",
        routes=len(routes), probes=len(probes),
    )

    brief = ""
    if use_analyst:
        brief = AnalystAgent(llm).run(ctx)
        tracer.decision("analysis complete", "give the migrator an explicit risk list instead of raw source only", brief=brief)

    lessons = ledger.context_block(exclude_case=case.id)
    if lessons:
        tracer.decision("memory injected", "rules distilled from failures on earlier cases", lessons=lessons)

    code = MigratorAgent(llm).run(ctx, brief, lessons)
    if not code:
        totals = tracer.finish({"status": "unparseable"})
        return CaseResult(case.id, "agent", ok=False,
                          error="the migrator produced nothing that parses as a module",
                          probes=len(probes), totals=totals, trace=str(tracer.path))

    report = _evaluate(ctx, code)
    tracer.decision(
        "first differential", "measure the migration against the recorded contract",
        **report.summary(),
    )

    turns = differential_runs = 0
    stop_reason = "parity reached on first attempt" if report.passed else ""
    tool_calls: list[str] = []

    if use_repair and not report.passed:
        outcome = RepairAgent(llm, tracer).run(ctx, code, report)
        if outcome.code:
            code = outcome.code
        if outcome.report:
            report = outcome.report
        turns, differential_runs = outcome.turns, outcome.differential_runs
        tool_calls, stop_reason = outcome.tool_calls, outcome.stop_reason
        tracer.decision("repair finished", stop_reason, **report.summary())

    lessons_added: list[str] = []
    # Reflection only earns its model call when there is a ledger to write to.
    # Without this the variants that have memory switched off still paid for a
    # reflection per failing case and threw the result away.
    if report.failures and ledger.enabled:
        rules = ReflectorAgent(llm).run(report)
        kinds = sorted({d.kind for d in report.failures})
        lessons_added = ledger.record(case.id, rules, kinds)
        if lessons_added:
            tracer.decision("lessons recorded", "generalise confirmed failures for later cases", lessons=lessons_added)

    output = output_path or (out_dir / f"{case.id}.py")
    if output.resolve() == Path(case.path).resolve():
        raise ValueError(
            f"refusing to write the migration over its own source file ({output})"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.bind(tracer)
    diff = unified_diff(case.source, code, case.id)
    summary = (
        f"\n=== {case.id}: {case.title} ===\n"
        f"behavioural parity {report.parity_strict:.1%} "
        f"({report.matched}/{report.total} probes reproduce the legacy response)\n"
        + ("" if report.passed else f"unresolved:\n{report.feedback(limit=4)}\n")
    )
    if checkpoint.approve(summary, diff):
        output.write_text(code, encoding="utf-8")
        written = str(output)
    else:
        written = None

    totals = tracer.finish({"status": "done", **report.summary()})
    return CaseResult(
        case.id, "agent", ok=True,
        parity_strict=report.parity_strict, parity_lenient=report.parity_lenient,
        probes=report.total, matched=report.matched, passed=report.passed,
        repair_turns=turns, differential_runs=differential_runs, tool_calls=tool_calls,
        lessons_added=lessons_added, error=report.migrated_error, totals=totals,
        parity_summary=report.summary(),
        failure_details=[d.render(max_body_chars=500) for d in report.failures],
        trace=str(tracer.path), output_file=written, stop_reason=stop_reason,
    )
