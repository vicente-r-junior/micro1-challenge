"""Behavioural comparison between the legacy app and the migrated app.

The legacy Flask responses are the ground truth. A migration is judged only by
whether the migrated app answers the *same probes* the *same way*. No model is
consulted here, which is the whole point: the oracle cannot be talked into
agreeing with the code it is judging.

Verdicts
--------
match            same status and same normalised body
body_differs     same status, different body
status_differs   different status within the same class (4xx vs 4xx)
class_differs    different status class, or one side errored
missing          the probe produced no response at all

``parity_strict`` (the headline metric) counts only ``match``.
``parity_lenient`` additionally accepts one documented divergence class:
Flask answering 400 where FastAPI answers 422 for the same invalid body. That
reclassification is arguably an improvement, so it is reported separately
instead of being hidden inside the headline number.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

_UUID = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
_ISO_TS = re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b")
_TMPPATH = re.compile(r"/(?:tmp|var/folders)/[^\s\"']+")

VALIDATION_PAIR = {(400, 422), (422, 400)}


def normalise(value: Any) -> Any:
    """Erase values that legitimately differ between two runs of the same app."""
    if isinstance(value, dict):
        return {k: normalise(value[k]) for k in sorted(value)}
    if isinstance(value, list):
        return [normalise(v) for v in value]
    if isinstance(value, str):
        text = _UUID.sub("<UUID>", value)
        text = _ISO_TS.sub("<TS>", text)
        text = _TMPPATH.sub("<PATH>", text)
        return text
    if isinstance(value, float):
        return round(value, 6)
    return value


def _class_of(status: Optional[int]) -> Optional[int]:
    return None if status is None else status // 100


def _body_is_application_output(status: Optional[int], content_type: Optional[str]) -> bool:
    """Should this response body be compared, or only its status?

    Only one thing gets a pass: the framework's own error page. Flask renders
    HTML for an unrouted 404 or a 405, FastAPI renders JSON, and no migration
    can or should reproduce that markup.

    Everything else is compared in full, including ``text/plain`` and
    ``text/csv``. An earlier version relaxed the check for *any* non-JSON body,
    which quietly stopped verifying the CSV export and the plain-text health
    endpoint -- 8 of 13 probes on one case were passing on the status code
    alone. A migration could have returned an empty CSV and scored 100%.
    """
    content_type = (content_type or "").lower()
    if "json" in content_type:
        return True
    is_framework_error_page = (status or 0) >= 400 and "html" in content_type
    return not is_framework_error_page


@dataclass
class ProbeDiff:
    probe_id: str
    kind: str
    route: str
    verdict: str
    expected_status: Optional[int]
    actual_status: Optional[int]
    expected_body: Any = None
    actual_body: Any = None
    note: str = ""

    @property
    def is_match(self) -> bool:
        return self.verdict == "match"

    @property
    def is_accepted_divergence(self) -> bool:
        return self.verdict == "status_differs" and (
            (self.expected_status, self.actual_status) in VALIDATION_PAIR
        )

    def render(self, *, max_body_chars: int = 400) -> str:
        def clip(value: Any) -> str:
            text = repr(value)
            return text if len(text) <= max_body_chars else text[:max_body_chars] + "…"

        lines = [
            f"probe {self.probe_id}  ({self.kind} on {self.route})",
            f"  expected: HTTP {self.expected_status}  {clip(self.expected_body)}",
            f"  actual:   HTTP {self.actual_status}  {clip(self.actual_body)}",
        ]
        if self.note:
            lines.append(f"  note: {self.note}")
        return "\n".join(lines)


@dataclass
class ParityReport:
    diffs: list[ProbeDiff] = field(default_factory=list)
    legacy_ok: bool = True
    migrated_ok: bool = True
    migrated_error: Optional[str] = None

    @property
    def total(self) -> int:
        return len(self.diffs)

    @property
    def matched(self) -> int:
        return sum(1 for d in self.diffs if d.is_match)

    @property
    def status_only(self) -> int:
        return sum(1 for d in self.diffs if d.is_match and d.note.startswith("status-only"))

    @property
    def accepted(self) -> int:
        return sum(1 for d in self.diffs if d.is_accepted_divergence)

    @property
    def failures(self) -> list[ProbeDiff]:
        return [d for d in self.diffs if not d.is_match]

    @property
    def parity_strict(self) -> float:
        return 0.0 if not self.total else self.matched / self.total

    @property
    def parity_lenient(self) -> float:
        return 0.0 if not self.total else (self.matched + self.accepted) / self.total

    @property
    def passed(self) -> bool:
        return self.migrated_ok and self.total > 0 and self.matched == self.total

    def summary(self) -> dict[str, Any]:
        by_kind: dict[str, dict[str, int]] = {}
        for diff in self.diffs:
            bucket = by_kind.setdefault(diff.kind, {"total": 0, "match": 0})
            bucket["total"] += 1
            bucket["match"] += int(diff.is_match)
        return {
            "probes": self.total,
            "matched": self.matched,
            "matched_status_only": self.status_only,
            "accepted_divergences": self.accepted,
            "parity_strict": round(self.parity_strict, 4),
            "parity_lenient": round(self.parity_lenient, 4),
            "app_imports": self.migrated_ok,
            "error": self.migrated_error,
            "by_kind": by_kind,
        }

    def feedback(self, limit: int = 8) -> str:
        """The text handed back to the repair agent. Diffs, not tracebacks."""
        if not self.migrated_ok:
            return (
                "The migrated app could not be imported or started at all.\n\n"
                f"{self.migrated_error}"
            )
        failures = self.failures
        if not failures:
            return "All probes match the legacy behaviour."
        head = (
            f"{len(failures)} of {self.total} probes do not reproduce the legacy "
            f"behaviour. The legacy Flask response is the required behaviour.\n"
        )
        shown = "\n\n".join(d.render() for d in failures[:limit])
        tail = f"\n\n… and {len(failures) - limit} more." if len(failures) > limit else ""
        return head + "\n" + shown + tail


def compare(
    probes: list[dict[str, Any]],
    legacy: list[dict[str, Any]],
    migrated: list[dict[str, Any]],
    *,
    migrated_ok: bool = True,
    migrated_error: Optional[str] = None,
) -> ParityReport:
    meta = {p["id"]: p for p in probes}
    left = {r["probe_id"]: r for r in legacy}
    right = {r["probe_id"]: r for r in migrated}

    report = ParityReport(migrated_ok=migrated_ok, migrated_error=migrated_error)

    for probe_id, expected in left.items():
        probe = meta.get(probe_id, {})
        actual = right.get(probe_id)
        exp_status = expected.get("status")
        exp_body = normalise(expected.get("json") if expected.get("json") is not None else expected.get("text"))

        if actual is None:
            report.diffs.append(
                ProbeDiff(
                    probe_id, probe.get("kind", "?"), probe.get("route", "?"),
                    "missing", exp_status, None, exp_body, None,
                    note="the migrated app never answered this probe",
                )
            )
            continue

        act_status = actual.get("status")
        act_body = normalise(actual.get("json") if actual.get("json") is not None else actual.get("text"))

        body_comparable = _body_is_application_output(exp_status, expected.get("content_type"))

        if exp_status == act_status and (body_comparable is False or exp_body == act_body):
            verdict = "match"
            note = "" if body_comparable else "status-only (legacy returned a framework error page)"
        elif exp_status == act_status:
            verdict, note = "body_differs", "status matches, response body does not"
        elif _class_of(exp_status) == _class_of(act_status):
            verdict = "status_differs"
            note = (
                "validation status reclassified (Flask 400 vs FastAPI 422)"
                if (exp_status, act_status) in VALIDATION_PAIR
                else "different status code within the same class"
            )
        else:
            verdict = "class_differs"
            note = actual.get("error") or "different status class"

        report.diffs.append(
            ProbeDiff(
                probe_id, probe.get("kind", "?"), probe.get("route", "?"),
                verdict, exp_status, act_status, exp_body, act_body, note,
            )
        )

    report.diffs.sort(key=lambda d: (d.is_match, d.probe_id))
    return report
