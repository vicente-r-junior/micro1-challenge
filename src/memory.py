"""Cross-case failure ledger.

The migration of case 7 should not repeat the mistake the agent already made on
case 3. After each case the orchestrator distils the *confirmed* behavioural
failures into short, general rules and stores them here; later migrations get
the most frequently hit rules injected into their context.

This is deliberately narrow. A lesson is only written when a differential run
proved a real behavioural break, so the ledger cannot fill up with the model's
opinions about what might go wrong. Every lesson keeps the cases and probe
kinds that produced it, so a reader can check the evidence behind each rule.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

DEFAULT_PATH = Path("data/memory/lessons.json")
MAX_INJECTED = 8


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


@dataclass
class Lesson:
    id: str
    rule: str
    probe_kinds: list[str] = field(default_factory=list)
    cases: list[str] = field(default_factory=list)
    hits: int = 0

    def merge(self, case_id: str, probe_kinds: list[str]) -> None:
        self.hits += 1
        if case_id not in self.cases:
            self.cases.append(case_id)
        for kind in probe_kinds:
            if kind not in self.probe_kinds:
                self.probe_kinds.append(kind)


class LessonLedger:
    def __init__(self, path: Path = DEFAULT_PATH, *, enabled: bool = True) -> None:
        self.path = Path(path)
        self.enabled = enabled
        self.lessons: dict[str, Lesson] = {}
        if self.path.exists():
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            for item in raw.get("lessons", []):
                self.lessons[item["id"]] = Lesson(**item)

    # -- read ---------------------------------------------------------------- #

    def context_block(self, exclude_case: Optional[str] = None) -> str:
        """The text injected into the migrator's prompt. Empty when disabled."""
        if not self.enabled or not self.lessons:
            return ""
        pool = [
            lesson
            for lesson in self.lessons.values()
            # A lesson learned only from this very case would leak the answer,
            # so a case never benefits from its own past failures.
            if not (exclude_case and lesson.cases == [exclude_case])
        ]
        if not pool:
            return ""
        pool.sort(key=lambda lesson: (-lesson.hits, lesson.id))
        lines = [
            f"{i}. {lesson.rule}  [hit {lesson.hits}x, e.g. {', '.join(lesson.cases[:3])}]"
            for i, lesson in enumerate(pool[:MAX_INJECTED], start=1)
        ]
        return (
            "Behaviour-preservation rules learned from earlier migrations in this "
            "benchmark. Each one comes from a differential test that actually "
            "failed:\n" + "\n".join(lines)
        )

    # -- write --------------------------------------------------------------- #

    def record(self, case_id: str, rules: list[str], probe_kinds: list[str]) -> list[str]:
        if not self.enabled:
            return []
        added: list[str] = []
        for rule in rules:
            rule = rule.strip()
            if len(rule) < 12:
                continue
            key = _slug(rule)
            if key in self.lessons:
                self.lessons[key].merge(case_id, probe_kinds)
            else:
                self.lessons[key] = Lesson(
                    id=key, rule=rule, probe_kinds=list(probe_kinds), cases=[case_id], hits=1
                )
                added.append(rule)
        self.flush()
        return added

    def flush(self) -> None:
        if not self.enabled:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "lessons": [asdict(lesson) for lesson in sorted(self.lessons.values(), key=lambda x: x.id)]
        }
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def stats(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "lessons": len(self.lessons),
            "total_hits": sum(lesson.hits for lesson in self.lessons.values()),
        }
