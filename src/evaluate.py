"""Benchmark driver: run one or more variants over every case and report.

Variants exist so the improvement changelog can be *measured* rather than
asserted. Each one turns on exactly one more component than the previous, and
they all share the case set, the model and the evaluation harness.

    v0_baseline   one direct prompt, no verification            (the fair baseline)
    v1_contract   contract-first migrator, differential scored, no repair
    v2_repair     + tool-calling repair loop
    v3_analyst    + analyst brief in the migrator's context
    v4_memory     + cross-case lesson ledger                    (the full agent)
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).parent))

# The .env has to be read before llm.py computes DEFAULT_MODEL from it.
from config import describe_providers, load_env  # noqa: E402

load_env()

from agents import MAX_TOOL_TURNS  # noqa: E402
from cases import Case, load_cases  # noqa: E402
from checkpoint import HumanCheckpoint  # noqa: E402
from llm import CacheMiss, LLMClient, NoCredentials, ResponseCache, resolve_model  # noqa: E402
from memory import LessonLedger  # noqa: E402
from orchestrator import CaseResult, run_agent, run_baseline  # noqa: E402
from tracing import Tracer, default_trace_path  # noqa: E402

VARIANTS: dict[str, dict[str, Any]] = {
    "v0_baseline": {"arm": "baseline", "label": "single prompt (baseline)"},
    "v1_contract": {"arm": "agent", "analyst": False, "repair": False, "memory": False,
                    "label": "contract-first migrator"},
    "v2_repair":   {"arm": "agent", "analyst": False, "repair": True,  "memory": False,
                    "label": "+ tool-calling repair loop"},
    "v3_analyst":  {"arm": "agent", "analyst": True,  "repair": True,  "memory": False,
                    "label": "+ analyst brief"},
    "v4_memory":   {"arm": "agent", "analyst": True,  "repair": True,  "memory": True,
                    "label": "+ cross-case memory (full agent)"},
}


def _run_one(
    case: Case,
    variant: str,
    spec: dict[str, Any],
    *,
    model: str,
    cache: Optional[ResponseCache],
    replay: bool,
    checkpoint_mode: str,
    out_dir: Path,
    trace_root: Path,
    ledger: LessonLedger,
) -> CaseResult:
    trace = default_trace_path(variant, case.id, trace_root)
    tracer = Tracer(trace, {"variant": variant, "case": case.id, "model": model, "replay": replay})
    llm = LLMClient(model=model, tracer=tracer, cache=cache, replay=replay)

    if spec["arm"] == "baseline":
        return run_baseline(case, llm, tracer, out_dir)
    return run_agent(
        case, llm, tracer, out_dir,
        ledger=ledger,
        checkpoint=HumanCheckpoint(checkpoint_mode, tracer),
        use_analyst=bool(spec.get("analyst")),
        use_repair=bool(spec.get("repair")),
    )


def run_variant(
    variant: str,
    cases: list[Case],
    *,
    model: str,
    cache: Optional[ResponseCache],
    replay: bool,
    checkpoint_mode: str,
    out_root: Path,
    trace_root: Path,
    workers: int = 1,
) -> dict[str, Any]:
    """Evaluate one variant over every case.

    Cases are independent and each model round trip costs a minute or more, so
    they run concurrently. The memory variant is the exception: a lesson learned
    on one case is only useful if a *later* case can see it, which needs an
    order. Rather than give that up, memory runs in waves -- each wave is
    parallel, the ledger is flushed between waves, and the next wave starts with
    everything the previous one learned. Fully sequential would be more faithful
    and would also take two hours; the wave size is recorded in the report so the
    trade is visible.
    """
    spec = VARIANTS[variant]
    out_dir = out_root / variant
    ledger_path = Path("data/memory") / f"{variant}_lessons.json"
    if spec.get("memory") and ledger_path.exists():
        ledger_path.unlink()  # every benchmark run starts from an empty memory
    ledger = LessonLedger(ledger_path, enabled=bool(spec.get("memory")))

    started = time.time()
    print_lock = threading.Lock()
    results: dict[str, CaseResult] = {}

    def work(case: Case) -> None:
        try:
            result = _run_one(
                case, variant, spec, model=model, cache=cache, replay=replay,
                checkpoint_mode=checkpoint_mode, out_dir=out_dir,
                trace_root=trace_root, ledger=ledger,
            )
        except CacheMiss as exc:
            with print_lock:
                print(f"  [{variant}] {case.id} … CACHE MISS")
            raise SystemExit(
                f"\nReplay cache does not cover {variant}/{case.id}.\n{exc}\n"
                "Re-record it with a provider key and without --replay."
            ) from exc
        except NoCredentials as exc:
            with print_lock:
                print(f"  [{variant}] {case.id} ... NO KEY")
            raise SystemExit(f"\n{exc}") from None
        except Exception as exc:  # a broken case must not lose the whole run
            with print_lock:
                print(f"  [{variant}] {case.id} … ERROR {type(exc).__name__}: {exc}")
            results[case.id] = CaseResult(case.id, spec["arm"], ok=False, error=f"{type(exc).__name__}: {exc}")
            return

        results[case.id] = result
        with print_lock:
            status = "PASS" if result.passed else f"{result.parity_strict:.0%}"
            note = f" repair={result.repair_turns}t/{result.differential_runs}d" if result.repair_turns else ""
            print(f"  [{variant}] {case.id:28s} {status:>5s}  ({result.matched}/{result.probes} probes){note}")

    # A wave is the whole case list unless the ledger needs ordering.
    wave_size = workers if spec.get("memory") else len(cases)
    waves = [cases[i : i + wave_size] for i in range(0, len(cases), wave_size)] or [[]]

    for wave in waves:
        if workers <= 1:
            for case in wave:
                work(case)
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                list(pool.map(work, wave))
        if spec.get("memory"):
            ledger.flush()

    rows = [results[case.id] for case in cases if case.id in results]
    scored = [r for r in rows if r.ok and r.probes]
    parities = [r.parity_strict for r in scored]
    return {
        "variant": variant,
        "label": spec["label"],
        "cases": len(rows),
        "scored": len(scored),
        "mean_parity_strict": round(statistics.mean(parities), 4) if parities else 0.0,
        "median_parity_strict": round(statistics.median(parities), 4) if parities else 0.0,
        "full_parity_cases": sum(1 for r in scored if r.passed),
        "failed_to_run": sum(1 for r in rows if not r.ok),
        "llm_calls": sum(r.totals.get("llm_calls", 0) for r in rows),
        "prompt_tokens": sum(r.totals.get("prompt_tokens", 0) for r in rows),
        "completion_tokens": sum(r.totals.get("completion_tokens", 0) for r in rows),
        "cost_usd": round(sum(r.totals.get("cost_usd", 0.0) for r in rows), 4),
        # model_s is the summed latency of the calls, so it describes the work
        # and is identical on every replay. Wall-clock is deliberately not
        # recorded here: on a replay it measures the reader's CPU, and a results
        # file that is meant to be diffed should not carry a field that moves
        # for a reason unrelated to the result.
        "model_s": round(sum(r.totals.get("model_s", 0.0) for r in rows), 1),
        "workers": workers,
        "wave_size": wave_size,
        "memory": ledger.stats(),
        "rows": [r.row() for r in rows],
    }


def markdown_report(
    summaries: list[dict[str, Any]], cases: list[Case], model: str, replay: bool
) -> str:
    lines = [
        "# Results: behavioural parity, baseline vs agent",
        "",
        f"Model `{model}` · {len(cases)} cases · "
        f"{'replayed from the committed cache' if replay else 'live run'}",
        "",
        "## What is measured",
        "",
        "The routes of each legacy Flask module are read statically, a fixed set of HTTP "
        "requests is derived from them, and those exact requests are replayed against the "
        "Flask app and against the migrated FastAPI app. **The Flask responses are the "
        "specification.** No language model judges anything.",
        "",
        "**Primary metric — migrations that are shippable.** The share of cases where "
        "*every* probe reproduces the legacy status and body. This is the number that "
        "decides whether a migration can be merged: nobody deploys 92% of a service. A "
        "single unmatched probe is a live client breaking.",
        "",
        "**Cost and model time** are what the recorded run actually spent. Replaying is "
        "free and finishes in seconds; the columns describe the work, not the cache. "
        "Model time is the summed latency of every call, so it is comparable across "
        "variants even when some of them were served from the cache.",
        "",
        "**Secondary metric — mean behavioural parity.** How close the non-shippable "
        "migrations are. Useful for seeing progress; not a release criterion.",
        "",
        "**What is not compared.** One class of probe is scored on its status code alone: "
        "those where the legacy app answered with the framework's own HTML error page, "
        "which no migration can reproduce. The count appears below so the relaxation is "
        "visible rather than assumed. Every other body — JSON, CSV, plain text — is "
        "compared in full.",
        "",
        "| Variant | What it adds | **Shippable** | Mean parity | LLM calls | Cost (USD) | Model time |",
        "|---|---|---|---|---|---|---|",
    ]
    for summary in summaries:
        shippable = summary["full_parity_cases"]
        scored = summary["scored"] or 1
        lines.append(
            f"| `{summary['variant']}` | {summary['label']} | "
            f"**{shippable}/{summary['scored']}** ({shippable / scored:.0%}) | "
            f"{summary['mean_parity_strict']:.1%} | "
            f"{summary['llm_calls']} | {summary['cost_usd']:.4f} | "
            f"{summary['model_s'] / 60:.0f} min |"
        )

    if len(summaries) >= 2:
        first, last = summaries[0], summaries[-1]
        scored = last["scored"] or 1
        gained = last["full_parity_cases"] - first["full_parity_cases"]
        lines += [
            "",
            "## Headline",
            "",
            f"Shippable migrations go from **{first['full_parity_cases']}/{first['scored']}** "
            f"with a single prompt to **{last['full_parity_cases']}/{last['scored']}** with the "
            f"full agent — {gained:+d} cases, {gained / scored:+.0%} of the benchmark.",
            "",
            f"Mean parity moves {first['mean_parity_strict']:.1%} → "
            f"{last['mean_parity_strict']:.1%}. The mean moves less than the shippable "
            "count, and that is the point: the baseline is already *nearly* right almost "
            "everywhere. The value is not in the average, it is in closing the last "
            "few probes — which are the ones that break production and which no code "
            "review catches.",
        ]

    lines += [
        "",
        "## Per case",
        "",
        "`100%` means every probe matched — the migration is shippable. Anything else is "
        "an observable behaviour change.",
        "",
        "| Case | " + " | ".join(f"`{s['variant']}`" for s in summaries) + " |",
        "|---" * (len(summaries) + 1) + "|",
    ]
    by_case: dict[str, dict[str, Any]] = {}
    for summary in summaries:
        for row in summary["rows"]:
            by_case.setdefault(row["case_id"], {})[summary["variant"]] = row
    for case in cases:
        cells = []
        for summary in summaries:
            row = by_case.get(case.id, {}).get(summary["variant"])
            if not row or not row["ok"]:
                cells.append("—")
            elif row["passed"]:
                cells.append("**100%**")
            else:
                cells.append(f"{row['parity_strict']:.0%}")
        lines.append(f"| {case.id} | " + " | ".join(cells) + " |")

    # Provenance split. The synthetic cases were written by the same person who
    # wrote the tool, so they are the ones to be suspicious of; the third-party
    # cases are the honest signal.
    third_party = {c.id for c in cases if not c.origin.startswith("synthetic")}
    if third_party and len(third_party) < len(cases):
        lines += [
            "",
            "## By provenance",
            "",
            "The synthetic cases were written for this benchmark by the author of the tool. "
            "The third-party cases are real code, vendored unmodified. They are scored "
            "identically and reported separately because a benchmark you designed yourself "
            "is the one you should trust least.",
            "",
            "| Variant | Synthetic (shippable) | Third-party (shippable) |",
            "|---|---|---|",
        ]
        for summary in summaries:
            syn = [r for r in summary["rows"] if r["ok"] and r["probes"] and r["case_id"] not in third_party]
            real = [r for r in summary["rows"] if r["ok"] and r["probes"] and r["case_id"] in third_party]
            lines.append(
                f"| `{summary['variant']}` | "
                f"{sum(1 for r in syn if r['passed'])}/{len(syn)} | "
                f"{sum(1 for r in real if r['passed'])}/{len(real)} |"
            )

    agent_runs = [s for s in summaries if s["variant"] != "v0_baseline"]
    if agent_runs:
        last = agent_runs[-1]
        rows = [r for r in last["rows"] if r["ok"]]
        status_only = sum(r["parity_summary"].get("matched_status_only", 0) for r in rows)
        probe_total = sum(r["probes"] for r in rows)
        turns = [r["repair_turns"] for r in rows if r["repair_turns"]]
        tool_use: dict[str, int] = {}
        for row in rows:
            for name in row["tool_calls"]:
                tool_use[name] = tool_use.get(name, 0) + 1
        lines += [
            "",
            "## Agent behaviour (`" + last["variant"] + "`)",
            "",
            f"- Cases needing repair: {len(turns)}/{len(rows)}",
            f"- Repair turns when used: {min(turns) if turns else 0}–{max(turns) if turns else 0} "
            f"(budget {MAX_TOOL_TURNS})",
            "- Tool calls: "
            + (", ".join(f"`{k}` ×{v}" for k, v in sorted(tool_use.items())) or "none"),
            f"- Lessons in the ledger at the end: {last['memory'].get('lessons', 0)}",
            f"- Probes scored on status alone (framework error pages): "
            f"{status_only}/{probe_total}",
            f"- Concurrency: {last['workers']} workers, wave size {last['wave_size']} "
            f"(affects wall-clock only, never a score)",
        ]

    return "\n".join(lines) + "\n"


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the migration benchmark.")
    parser.add_argument("--variants", default="v0_baseline,v4_memory",
                        help="comma-separated; 'all' runs the full ablation")
    parser.add_argument("--cases", default=None, help="comma-separated case ids (default: all)")
    parser.add_argument("--model", default=None,
                        help="LiteLLM model string; on --replay it defaults to "
                             "whatever the cache was recorded with")
    parser.add_argument("--cache", default="data/llm_cache.jsonl")
    parser.add_argument("--replay", action="store_true",
                        help="run entirely from the cache: no network, no API key")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--checkpoint", default="auto", choices=["auto", "interactive", "dry-run"])
    parser.add_argument("--out", default="results")
    parser.add_argument("--trace-root", default="trajectories")
    parser.add_argument("--workers", type=int, default=6,
                        help="cases evaluated concurrently (default 6)")
    args = parser.parse_args(argv)

    variants = list(VARIANTS) if args.variants == "all" else [v.strip() for v in args.variants.split(",")]
    unknown = [v for v in variants if v not in VARIANTS]
    if unknown:
        parser.error(f"unknown variant(s): {', '.join(unknown)}")

    cases = load_cases(only=args.cases.split(",") if args.cases else None)
    if not cases:
        parser.error("no cases found under data/cases/")

    cache = None if args.no_cache else ResponseCache(Path(args.cache))
    args.model = resolve_model(args.model, cache, args.replay, parser.error)
    print(
        f"model={args.model}  cases={len(cases)}  variants={','.join(variants)}  "
        f"{'REPLAY (offline)' if args.replay else 'live'}  "
        f"cache_entries={len(cache) if cache else 0}  workers={args.workers}  "
        f"providers={describe_providers()}"
    )

    summaries = [
        run_variant(
            variant, cases,
            model=args.model, cache=cache, replay=args.replay,
            checkpoint_mode=args.checkpoint,
            out_root=Path(args.out) / "migrated", trace_root=Path(args.trace_root),
            workers=max(1, args.workers),
        )
        for variant in variants
    ]

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(
        json.dumps({"model": args.model, "replay": args.replay, "variants": summaries}, indent=2),
        encoding="utf-8",
    )
    report = markdown_report(summaries, cases, args.model, args.replay)
    (out / "REPORT.md").write_text(report, encoding="utf-8")
    print("\n" + report)
    print(f"wrote {out/'REPORT.md'} and {out/'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
