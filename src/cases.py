"""Benchmark case loading.

A case is a directory under ``data/cases/`` holding the legacy Flask module and
a ``case.json`` describing it. The metadata records where the code came from and
under which licence, because part of the submission is being able to say exactly
what existed before this project and what was written for it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

CASES_DIR = Path("data/cases")


@dataclass
class Case:
    id: str
    title: str
    path: Path
    origin: str
    licence: str
    tier: str
    notes: str
    source: str
    probe_headers: dict[str, str] = field(default_factory=dict)
    path_values: dict[str, str] = field(default_factory=dict)
    body_values: dict[str, Any] = field(default_factory=dict)

    @property
    def runnable(self) -> bool:
        """Tier A cases can be executed; tier B are real-world fragments."""
        return self.tier == "A"


def load_case(directory: Path) -> Case:
    meta_path = directory / "case.json"
    meta: dict[str, Any] = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    app_file = directory / "legacy_app.py"
    return Case(
        id=meta.get("id", directory.name),
        title=meta.get("title", directory.name),
        path=directory,
        origin=meta.get("origin", "unspecified"),
        licence=meta.get("licence", "unspecified"),
        tier=meta.get("tier", "A"),
        notes=meta.get("notes", ""),
        source=app_file.read_text(encoding="utf-8"),
        # Fixture credentials/headers the probes need to reach past a guard.
        # Declared by the case, never guessed by the harness.
        probe_headers=meta.get("probe_headers", {}),
        path_values=meta.get("path_values", {}),
        body_values=meta.get("body_values", {}),
    )


def load_cases(root: Path = CASES_DIR, only: Optional[list[str]] = None) -> list[Case]:
    cases = [
        load_case(d)
        for d in sorted(root.iterdir())
        if d.is_dir() and (d / "legacy_app.py").exists()
    ]
    if only:
        wanted = set(only)
        cases = [c for c in cases if c.id in wanted or c.path.name in wanted]
    return cases
