"""Render an agent trajectory as something a person can read.

The JSONL under `trajectories/` is complete but not friendly. This prints the
same run as a narrative: what the agent was asked, what it decided, which tools
it reached for and what came back.

    python src/show_trajectory.py trajectories/v4_memory/case_01_inventory.jsonl
    python src/show_trajectory.py <file> --full      # include whole prompts
    python src/show_trajectory.py <file> --compact   # actions only, one screen

The default view is the auditable one and runs past a hundred lines. `--compact`
exists to be *watched*: it drops the prompts, summarises each tool result in a
line of English, and colours the parts that carry the story.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

RULE = "─" * 78

# ANSI, applied only when stdout is a terminal and the reader has not opted out.
# A trajectory piped into a file or a diff has to stay plain text.
_ANSI = {
    "dim": "\033[2m", "bold": "\033[1m", "reset": "\033[0m",
    "green": "\033[32m", "red": "\033[31m", "yellow": "\033[33m",
    "blue": "\033[34m", "magenta": "\033[35m", "cyan": "\033[36m",
}
_USE_COLOUR = False


def c(text: str, *styles: str) -> str:
    """Wrap text in ANSI styles, or return it untouched when colour is off."""
    if not _USE_COLOUR or not styles:
        return text
    return "".join(_ANSI[s] for s in styles) + text + _ANSI["reset"]


def clip(text: Any, limit: int) -> str:
    text = "" if text is None else str(text)
    text = text.strip()
    if limit <= 0 or len(text) <= limit:
        return text
    return text[:limit] + f"\n  … [{len(text) - limit} more characters]"


def summarise_result(tool: str, result: dict[str, Any]) -> str:
    """One readable line per tool result, instead of truncated JSON.

    A JSON blob cut off mid-key hides the thing worth seeing: three searches in
    a row finding nothing, and parity jumping to 100% on the first candidate.
    """
    if result.get("error"):
        return c(str(result["error"])[:120], "red")

    if tool == "record_contract":
        return c(f"recorded {result.get('responses', '?')} responses from the legacy app", "green")

    if tool == "search_legacy":
        hits = result.get("matches") or []
        if not hits:
            return c("no matches", "red", "bold")
        first = hits[0]
        more = f"  (+{len(hits) - 1} more)" if len(hits) > 1 else ""
        return (c(f"{len(hits)} match" + ("es" if len(hits) != 1 else ""), "green")
                + c(f"   line {first['line']}: {first['text'].strip()[:66]}{more}", "dim"))

    if tool == "get_probe_detail":
        req = result.get("request") or {}
        legacy = result.get("legacy_response") or {}
        cand = result.get("candidate_response") or {}

        def body(d: dict[str, Any]) -> str:
            value = d.get("body")
            return json.dumps(value, ensure_ascii=False)[:46] if value is not None else "-"

        return (c(f"{req.get('method', '?')} {req.get('path', '?')}", "dim")
                + c(f"   legacy {legacy.get('status')} {body(legacy)}", "green")
                + c(f"   got {cand.get('status')} {body(cand)}", "red"))

    if tool == "run_differential":
        parity = result.get("parity_strict")
        if parity is None:
            return c(json.dumps(result, ensure_ascii=False)[:120], "yellow")
        styles = ("green", "bold") if parity == 1.0 else ("yellow",)
        return (c(f"parity {parity:.0%}", *styles)
                + c(f"   {result.get('matched')}/{result.get('probes')} probes"
                    f"   budget left {result.get('budget_left')}", "dim"))

    if tool == "submit":
        return c("submitted", "green")
    return json.dumps(result, ensure_ascii=False)[:140]


def render(path: Path, limit: int, compact: bool = False) -> str:
    out: list[str] = []
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    for event in events:
        stamp = f"{event['t_rel_s']:7.1f}s"
        kind = event["kind"]

        if kind == "run_start":
            out += [
                c(RULE, "dim"),
                c(f"RUN {event['run_id']}", "bold")
                + f"  variant={event.get('variant', '?')}  case={event.get('case', '?')}"
                + f"  model={event.get('model', '?')}"
                + (c("  [replayed from cache]", "dim") if event.get("replay") else ""),
                c(RULE, "dim"),
            ]

        elif kind == "llm_call":
            tag = event["tag"].split(" ")[0]
            cost = f" ${event['cost_usd']:.4f}" if event.get("cost_usd") else " cost n/a"
            if compact:
                out.append(
                    c(stamp, "dim") + "  " + c(f"[{tag}]", "magenta", "bold")
                    + c(f" {event['prompt_tokens']}→{event['completion_tokens']} tok{cost}", "dim")
                )
                continue
            out += [
                "",
                f"{stamp}  ── {event['tag'].upper()} ── "
                f"{event['prompt_tokens']}→{event['completion_tokens']} tok · "
                f"{event['latency_s']:.1f}s ·{cost}",
                "  SYSTEM:", "  " + clip(event["system"], limit).replace("\n", "\n  "),
                "  INPUT:", "  " + clip(event["user"], limit).replace("\n", "\n  "),
                "  OUTPUT:", "  " + clip(event["completion"], limit).replace("\n", "\n  "),
            ]

        elif kind == "tool_call":
            args = {k: clip(v, 160) for k, v in (event.get("args") or {}).items()}
            if compact:
                shown = {k: v for k, v in args.items() if k != "code"}
                label = json.dumps(shown, ensure_ascii=False)[:104] if shown else "<a complete module>"
                out.append(c(stamp, "dim") + "  " + c("→ ", "cyan")
                           + c(event["tool"], "cyan", "bold") + c(f" {label}", "dim"))
            else:
                out.append(f"{stamp}  → tool {event['tool']}({json.dumps(args, ensure_ascii=False)[:300]})")

        elif kind == "tool_result":
            if compact:
                out.append(" " * 12 + c("← ", "dim") + summarise_result(event["tool"], event["result"]))
            else:
                out.append(f"{stamp}  ← {event['tool']}: {json.dumps(event['result'], ensure_ascii=False)[:400]}")

        elif kind == "decision":
            detail = {
                k: v for k, v in event.items()
                if k not in {"seq", "run_id", "t_rel_s", "kind", "what", "why", "by_kind"}
            }
            out += [
                "",
                c(stamp, "dim") + "  " + c(f"★ {event['what'].upper()}", "yellow", "bold"),
                c(f"           {event['why']}", "dim"),
            ]
            if compact:
                keep = {k: detail[k] for k in ("parity_strict", "matched", "probes") if k in detail}
                if keep:
                    out.append("           " + c(json.dumps(keep), "dim"))
            elif detail:
                out.append(f"           {json.dumps(detail, ensure_ascii=False, default=str)[:400]}")

        elif kind == "human_checkpoint":
            out.append(c(stamp, "dim") + "  "
                       + c(f"⏸ HUMAN [{event['mode']}] answered {event['answer']!r}", "blue", "bold"))

        elif kind == "run_end":
            totals = event["totals"]
            outcome = event["outcome"]
            parity = outcome.get("parity_strict")
            verdict = ""
            if parity is not None:
                styles = ("green", "bold") if parity == 1.0 else ("yellow", "bold")
                verdict = c(f"parity {parity:.0%}", *styles) + c(
                    f"   {outcome.get('matched')}/{outcome.get('probes')} probes", "dim")
            out += [
                "",
                c(RULE, "dim"),
                "END  " + (verdict or json.dumps(outcome, ensure_ascii=False, default=str)[:200]),
                c(f"     {totals['llm_calls']} calls · "
                  f"{totals['prompt_tokens']}→{totals['completion_tokens']} tok · "
                  f"${totals['cost_usd']:.4f} · {totals['wall_s']:.0f}s", "dim"),
                c(RULE, "dim"),
            ]
    return "\n".join(out)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Pretty-print an agent trajectory.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--full", action="store_true", help="do not truncate prompts")
    parser.add_argument("--compact", action="store_true",
                        help="actions only, no prompts — fits on one screen")
    parser.add_argument("--limit", type=int, default=600, help="characters per field (default 600)")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colour")
    args = parser.parse_args(argv)

    global _USE_COLOUR
    _USE_COLOUR = not args.no_color and sys.stdout.isatty() and not os.getenv("NO_COLOR")

    if not args.path.is_file():
        print(f"error: {args.path} not found", file=sys.stderr)
        return 2
    print(render(args.path, 0 if args.full else args.limit, compact=args.compact))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
