"""Human approval gate.

Ground rule 4 of the challenge requires consequential actions to sit behind a
human checkpoint. Writing a generated module over a real service's source is
consequential, so nothing reaches disk until a person says so.

Three modes exist and every one of them is recorded in the trajectory:

``interactive``  ask on stdin (the default when a human is driving)
``auto``         approve without asking, for benchmark runs where the output
                 goes to a results directory and never to a real repository
``dry-run``      never write, whatever the answer
"""

from __future__ import annotations

from typing import Callable, Optional

from tracing import Tracer

PROMPT = "Apply this migration to disk?  [y] write   [n] discard   [d] full diff  : "


class HumanCheckpoint:
    def __init__(
        self,
        mode: str = "interactive",
        tracer: Optional[Tracer] = None,
        prompt_func: Callable[[str], str] = input,
    ) -> None:
        if mode not in {"interactive", "auto", "dry-run"}:
            raise ValueError(f"unknown checkpoint mode {mode!r}")
        self.mode = mode
        self._tracer = tracer
        self._prompt = prompt_func

    def bind(self, tracer: Optional[Tracer]) -> None:
        """Attach a tracer if the caller did not supply one at construction.

        The approval decision is the audit record for ground rule 4; a
        checkpoint that runs without a tracer would leave no evidence that a
        human was asked, so the orchestrator binds one defensively.
        """
        if self._tracer is None:
            self._tracer = tracer

    def approve(self, summary: str, diff: str) -> bool:
        if self.mode == "dry-run":
            self._log("(not asked)", "dry-run")
            return False
        if self.mode == "auto":
            self._log("(not asked)", "auto")
            return True

        # The full diff of a Flask module against its FastAPI rewrite is a
        # whole-file replacement -- hundreds of lines that tell a reviewer
        # nothing. Lead with the evidence that decides the answer and keep the
        # diff one keystroke away.
        print(summary)
        print(_diffstat(diff))
        while True:
            answer = self._prompt(PROMPT).strip().lower()
            if answer in ("d", "diff"):
                print(diff)
                continue
            approved = answer in ("y", "yes")
            self._log(answer or "<empty>", "interactive")
            return approved

    def _log(self, answer: str, mode: str) -> None:
        if self._tracer:
            self._tracer.human_checkpoint(PROMPT, answer, mode)


def _diffstat(diff: str) -> str:
    added = sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))
    return f"  diff: +{added} / -{removed} lines  (press d to read it in full)"
