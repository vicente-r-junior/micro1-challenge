"""Migrate one Flask module to FastAPI, with evidence.

This is the entry point a person actually uses. Point it at a Flask file and it
will record what that file does today, migrate it, prove whether the migration
still does the same thing, and show you the diff before anything is written.

    python src/migrate.py path/to/app.py

Nothing reaches disk without approval. The run leaves three artefacts next to
the output: the migrated module, a migration report you can attach to the pull
request, and the full agent trajectory.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

# The .env has to be read before llm.py computes DEFAULT_MODEL from it.
from config import describe_providers, load_env  # noqa: E402

load_env()

from cases import Case  # noqa: E402
from checkpoint import HumanCheckpoint  # noqa: E402
from llm import CacheMiss, LLMClient, ResponseCache, resolve_model  # noqa: E402
from memory import DEFAULT_PATH, LessonLedger  # noqa: E402
from orchestrator import run_agent  # noqa: E402
from tracing import Tracer  # noqa: E402


def migration_report(case: Case, result, model: str, trace: Path) -> str:
    """The document a reviewer reads before approving the pull request."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    verdict = (
        "**Behaviour preserved.** Every recorded request produces the same status "
        "and the same response body as the Flask original."
        if result.passed
        else "**Behaviour NOT fully preserved.** The differences below are real and "
        "need a human decision before this is merged."
    )

    lines = [
        f"# Migration report — `{case.id}`",
        "",
        f"{case.title} · {stamp} · model `{model}`",
        "",
        "## Verdict",
        "",
        verdict,
        "",
        f"- Behavioural parity: **{result.parity_strict:.1%}** "
        f"({result.matched}/{result.probes} probes reproduce the legacy response)",
        f"- Probes replayed against both apps: {result.probes}",
        f"- Repair turns used: {result.repair_turns} · differential runs: {result.differential_runs}",
        "",
        "## How this was checked",
        "",
        "The routes of the original module were read statically, a fixed set of HTTP "
        "requests was derived from them, and those exact requests were replayed "
        "against the Flask app and against the migrated FastAPI app. The Flask "
        "responses are the specification. No language model judged the result.",
        "",
    ]

    if result.failure_details:
        lines += ["## Differences that remain", ""]
        for detail in result.failure_details:
            lines += ["```", detail, "```", ""]
        lines += [
            "Each of these is a change an existing client would observe. Decide "
            "case by case whether it is acceptable before merging.",
            "",
        ]

    summary = result.parity_summary
    if summary:
        lines += [
            "## Probe breakdown",
            "",
            "| Probe kind | Matched | Total |",
            "|---|---|---|",
        ]
        for kind, bucket in sorted(summary.get("by_kind", {}).items()):
            lines.append(f"| {kind} | {bucket['match']} | {bucket['total']} |")
        if summary.get("matched_status_only"):
            lines += [
                "",
                f"{summary['matched_status_only']} probe(s) were compared on status only, "
                "because the legacy app answered them with the framework's built-in HTML "
                "error page rather than with application output.",
            ]
        if summary.get("accepted_divergences"):
            lines += [
                "",
                f"{summary['accepted_divergences']} probe(s) differ only by Flask's 400 "
                "becoming FastAPI's 422 on invalid input. That is arguably an improvement, "
                "but it is still a change your clients will see, so it is counted as a "
                "failure in the headline number.",
            ]

    lines += [
        "",
        "## Provenance",
        "",
        f"- Source module: `{case.path}`",
        f"- Agent trajectory: `{trace}`",
        f"- Tokens: {result.totals.get('prompt_tokens', 0)} in / "
        f"{result.totals.get('completion_tokens', 0)} out · "
        f"cost ${result.totals.get('cost_usd', 0):.4f} · "
        f"{result.totals.get('wall_s', 0):.0f}s wall clock",
        "",
    ]
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Migrate a Flask module to FastAPI and prove the behaviour is unchanged."
    )
    parser.add_argument("source", type=Path, help="the legacy Flask module")
    parser.add_argument("--out", type=Path, default=None, help="output .py (default: <name>_fastapi.py)")
    parser.add_argument("--model", default=None,
                        help="LiteLLM model string; on --replay it defaults to "
                             "whatever the cache was recorded with")
    parser.add_argument("--cache", default="data/llm_cache.jsonl")
    parser.add_argument("--replay", action="store_true", help="offline, from the shipped cache")
    parser.add_argument("--yes", action="store_true", help="skip the approval prompt (CI use)")
    parser.add_argument("--dry-run", action="store_true", help="never write, whatever the answer")
    parser.add_argument("--no-memory", action="store_true")
    args = parser.parse_args(argv)

    if not args.source.is_file():
        print(f"error: {args.source} is not a readable file", file=sys.stderr)
        return 2

    case = Case(
        id=args.source.stem,
        title=f"migration of {args.source.name}",
        path=args.source,
        origin="user-supplied",
        licence="unknown",
        tier="A",
        notes="",
        source=args.source.read_text(encoding="utf-8"),
    )

    cache = ResponseCache(Path(args.cache))
    args.model = resolve_model(args.model, cache, args.replay, lambda m: parser.error(m))

    out_path = args.out or args.source.with_name(f"{args.source.stem}_fastapi.py")
    trace = Path("trajectories") / "migrate" / f"{case.id}.jsonl"
    tracer = Tracer(trace, {"entrypoint": "migrate", "source": str(args.source), "model": args.model})

    mode = "dry-run" if args.dry_run else ("auto" if args.yes else "interactive")

    try:
        llm = LLMClient(model=args.model, tracer=tracer, cache=cache, replay=args.replay)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"reading {args.source} …  (model {args.model}, providers: {describe_providers()})")
    try:
        result = run_agent(
            case, llm, tracer, out_path.parent,
            ledger=LessonLedger(DEFAULT_PATH, enabled=not args.no_memory),
            checkpoint=HumanCheckpoint(mode, tracer),
            output_path=out_path,
        )
    except CacheMiss as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not result.ok:
        print(f"migration could not be evaluated: {result.error}", file=sys.stderr)
        return 1

    report_path = out_path.with_name(f"{out_path.stem}_MIGRATION_REPORT.md")
    report_path.write_text(migration_report(case, result, args.model, trace), encoding="utf-8")

    print(f"\nbehavioural parity: {result.parity_strict:.1%} "
          f"({result.matched}/{result.probes} probes)")
    if result.output_file:
        print(f"migrated module:    {out_path}")
    else:
        print("migrated module:    not written (approval declined)")
    print(f"migration report:   {report_path}")
    print(f"agent trajectory:   {trace}")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
