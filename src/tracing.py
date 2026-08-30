"""Trajectory logging.

Every LLM call, every sandbox execution and every decision the agent makes is
appended to a JSONL file. This is what makes an agent run auditable after the
fact: the submission's `trajectories/` directory is produced entirely by this
module, and the numbers in `results/` are derived from the same records.

Design notes
------------
* One JSONL file per run. Append-only, flushed on every write, so a crashed run
  still leaves a readable trajectory.
* Prompts and completions are stored verbatim. Truncating them would defeat the
  purpose (a reader must be able to see exactly what the model was told).
* Token counts and cost are recorded per call so the totals in the report are
  measured, not estimated.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional

SCHEMA_VERSION = 1

# USD per 1M tokens. Used only to report cost; unknown models fall back to 0.0
# and the report says so rather than inventing a number.
PRICING_USD_PER_MTOK: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-5": (1.25, 10.00),
    "gpt-5-mini": (0.25, 2.00),
}


def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> Optional[float]:
    key = model.split(":")[-1]
    price = PRICING_USD_PER_MTOK.get(key)
    if price is None:
        for known, value in PRICING_USD_PER_MTOK.items():
            if key.startswith(known):
                price = value
                break
    if price is None:
        return None
    inp, out = price
    return (prompt_tokens / 1_000_000) * inp + (completion_tokens / 1_000_000) * out


class Tracer:
    """Append-only JSONL trajectory writer."""

    def __init__(self, path: Path, run_meta: Optional[dict[str, Any]] = None) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id = uuid.uuid4().hex[:12]
        self._t0 = time.time()
        self._seq = 0
        self.totals = {
            "llm_calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cost_usd": 0.0,
            # Time the models actually spent, summed from the recorded latency
            # of each call. Unlike wall-clock this is comparable across runs:
            # a replayed variant finishes in seconds but the work it stands for
            # did not, and a column that said 4s would be describing the cache.
            "model_s": 0.0,
        }
        self._cost_known = True
        # Truncate: a run owns its file.
        self.path.write_text("", encoding="utf-8")
        self.event("run_start", {"schema_version": SCHEMA_VERSION, **(run_meta or {})})

    # -- core ------------------------------------------------------------- #

    def event(self, kind: str, payload: dict[str, Any]) -> None:
        self._seq += 1
        record = {
            "seq": self._seq,
            "run_id": self.run_id,
            "t_rel_s": round(time.time() - self._t0, 3),
            "kind": kind,
            **payload,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            handle.flush()

    # -- typed helpers ------------------------------------------------------ #

    def llm_call(
        self,
        *,
        tag: str,
        model: str,
        system: str,
        user: str,
        completion: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_s: float,
        attempt: int,
        cost_usd: Optional[float] = None,
    ) -> None:
        # LiteLLM reports the real cost when it knows the model; the local table
        # is only a fallback, and an unknown model reports no cost at all rather
        # than a made-up one.
        cost = cost_usd if cost_usd is not None else estimate_cost_usd(model, prompt_tokens, completion_tokens)
        if cost is None:
            self._cost_known = False
        self.totals["llm_calls"] += 1
        self.totals["prompt_tokens"] += prompt_tokens
        self.totals["completion_tokens"] += completion_tokens
        self.totals["cost_usd"] += cost or 0.0
        self.totals["model_s"] += latency_s
        self.event(
            "llm_call",
            {
                "tag": tag,
                "attempt": attempt,
                "model": model,
                "latency_s": round(latency_s, 3),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost_usd": cost,
                "system": system,
                "user": user,
                "completion": completion,
            },
        )

    def tool_call(self, name: str, args: dict[str, Any]) -> None:
        self.event("tool_call", {"tool": name, "args": args})

    def tool_result(self, name: str, result: dict[str, Any]) -> None:
        self.event("tool_result", {"tool": name, "result": result})

    def decision(self, what: str, why: str, **extra: Any) -> None:
        self.event("decision", {"what": what, "why": why, **extra})

    def human_checkpoint(self, prompt: str, answer: str, mode: str) -> None:
        self.event("human_checkpoint", {"prompt": prompt, "answer": answer, "mode": mode})

    def finish(self, outcome: dict[str, Any]) -> dict[str, Any]:
        summary = {
            **self.totals,
            "cost_usd": round(self.totals["cost_usd"], 6),
            "model_s": round(self.totals["model_s"], 1),
            "cost_is_complete": self._cost_known,
            "wall_s": round(time.time() - self._t0, 3),
        }
        self.event("run_end", {"outcome": outcome, "totals": summary})
        return summary


def default_trace_path(arm: str, case_id: str, root: str | os.PathLike[str] = "trajectories") -> Path:
    return Path(root) / arm / f"{case_id}.jsonl"
