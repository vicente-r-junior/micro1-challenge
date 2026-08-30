"""Copy the coding-agent session transcript into the submission, redacted.

The challenge asks for trajectories from *every* agent used, which includes the
coding agent that built the project. That transcript is a raw session log: it
was never written with publication in mind, so it is scrubbed on the way in
rather than trusted.

    python scripts/prepare_build_trajectory.py

Redaction is deliberately over-eager. A false positive costs a reader one
unreadable token; a false negative publishes a credential.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any


def _parses(line: str) -> bool:
    try:
        json.loads(line)
    except json.JSONDecodeError:
        return False
    return True

DEST = Path("trajectories/build")

README_TEMPLATE = """\
# Build trajectory — the session that produced this project

`claude-code-session-62fa5efb.jsonl` is the complete, unedited session log of
the coding agent used to build this submission, disclosed under the challenge's
agent-use requirement and described in [`docs/agent-use.md`](../../docs/agent-use.md).

Credentials and token-shaped strings were redacted by
[`scripts/prepare_build_trajectory.py`](../../scripts/prepare_build_trajectory.py)
before the file was copied here. The script re-parses everything it writes and
refuses to ship a transcript that no longer decodes ({redactions} redactions applied), so the file is valid JSONL.

## A note on language

The author is Brazilian and the working conversation is **bilingual** —
instructions in Portuguese, reasoning and output in English. Roughly twenty of
the author's messages are in Portuguese; everything else in the file is English.

**The log is not translated, on purpose.** A trajectory is a record of what
happened. Machine-translating six megabytes of it would produce a document that
is neither what was said nor reliably accurate, and would quietly replace
evidence with a paraphrase. The index below exists so the file can be navigated
without reading Portuguese.

Everything that is *not* a record of the conversation is in English by design:

| Artefact | Language |
|---|---|
| All source, comments and docstrings | English |
| README, changelog, reproduction guide, all of `docs/` | English |
| The four agents' prompts, and their trajectories under `trajectories/v*/` | English |
| This build log | Bilingual, unedited |

## What happened, in order

A reader who wants the short version should read
[`CHANGELOG.md`](../../CHANGELOG.md) — every entry below is documented there
with its evidence.

**1. The original design was thrown away.** The project began as an LLM writing
the migration and a second LLM call writing tests *for that migration*. It is
preserved at [`docs/superseded/`](../../docs/superseded/). It was abandoned
before any measurement because the defect is structural: a test generated from
the migrated code asserts whatever the migration decided.

**2. The oracle moved out of the model's reach.** Routes are read from the
legacy source with `ast`, probes are derived from them by fixed rules, and those
probes are replayed against the *original Flask app*. Its answers became the
specification.

**3. The harness was wrong several times before it was right.** Fifteen
corrections are documented in `CHANGELOG.md` Part 2. The ones worth reading are
the three that produced confident, plausible, wrong numbers: a response cache
that could never record its first entry (an empty cache is falsy in Python), a
parser failure scored as a failed migration, and a reproduction command that
worked only on the machine that built it.

**4. A benchmark was built, and then distrusted.** Fourteen synthetic cases plus
two real third-party modules. The baseline passed twelve of the author's own
fourteen and zero of the two it had not seen — which reframed the whole project.

**5. The agent was measured component by component.** Five variants, each adding
one part. Two of them — the analyst brief and the cross-case memory — cost 60%
more for zero additional shippable migrations and were removed.

**6. The result was replicated.** Seven baseline runs across five models and two
vendors, including two models run twice from scratch, to find out how much a
single sample is worth. The answer: the synthetic score moves by up to three
cases and the model ordering reverses; the third-party column does not move at
all.

## Reading the file

Each line is one JSON record. The largest fields are tool results and file
contents.

```bash
# every message the author typed, one per line
jq -r 'select(.type=="user") | .message.content | strings' \
   claude-code-session-62fa5efb.jsonl | head -60
```


The agents that *are* the project have their own trajectories, in English, under
`trajectories/v0_baseline/` through `trajectories/v4_memory/`, plus the
cross-model runs. Render any of them:

```bash
python src/show_trajectory.py trajectories/v2_repair/case_14_restful_todo_simple.jsonl --compact
```
"""

# Ordered most specific first, so a provider-shaped key is labelled as such.
PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"), "<REDACTED:anthropic-key>"),
    (re.compile(r"sk-proj-[A-Za-z0-9_\-]{20,}"), "<REDACTED:openai-key>"),
    (re.compile(r"\bsk-[A-Za-z0-9]{24,}"), "<REDACTED:api-key>"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"), "<REDACTED:github-token>"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "<REDACTED:aws-key-id>"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}"), "<REDACTED:slack-token>"),
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}"), "<REDACTED:jwt>"),
    (re.compile(r"(?i)\b([A-Z0-9_]*(?:API_KEY|SECRET|TOKEN|PASSWORD))\s*=\s*[^\s\"',}]{8,}"), r"\1=<REDACTED>"),
]


def scrub(text: str) -> tuple[str, int]:
    """Redact secrets from a plain string."""
    total = 0
    for pattern, replacement in PATTERNS:
        text, count = pattern.subn(replacement, text)
        total += count
    return text, total


def _scrub_value(value: Any) -> tuple[Any, int]:
    """Recursively redact the string values of a decoded JSON structure."""
    if isinstance(value, str):
        return scrub(value)
    if isinstance(value, list):
        total = 0
        out = []
        for item in value:
            cleaned, count = _scrub_value(item)
            out.append(cleaned)
            total += count
        return out, total
    if isinstance(value, dict):
        total = 0
        out = {}
        for key, item in value.items():
            cleaned, count = _scrub_value(item)
            out[key] = cleaned
            total += count
        return out, total
    return value, 0


def scrub_jsonl(text: str) -> tuple[str, int, int]:
    """Redact a JSONL file without breaking it.

    Running a regex over the raw text corrupts the file: a match can swallow a
    backslash that was part of a JSON escape, and the line stops parsing. Three
    of 1299 lines broke that way before this existed. Each line is therefore
    decoded, scrubbed value by value, and re-encoded, so the output is valid by
    construction. A line that will not decode is scrubbed as raw text and
    counted, rather than being dropped.
    """
    out: list[str] = []
    redactions = 0
    unparsed = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            cleaned, count = scrub(line)
            out.append(cleaned)
            redactions += count
            unparsed += 1
            continue
        cleaned_record, count = _scrub_value(record)
        out.append(json.dumps(cleaned_record, ensure_ascii=False))
        redactions += count
    return "\n".join(out) + "\n", redactions, unparsed


def main() -> int:
    source_dir = Path.home() / ".claude" / "projects" / "-Users-vicentejr-dev-micro1-challenge"
    transcripts = sorted(source_dir.glob("*.jsonl")) if source_dir.exists() else []
    if not transcripts:
        print(f"no session transcript found under {source_dir}", file=sys.stderr)
        return 1

    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)

    grand_total = 0
    for transcript in transcripts:
        raw = transcript.read_text(encoding="utf-8", errors="ignore")
        cleaned, count, unparsed = scrub_jsonl(raw)
        target = DEST / f"claude-code-session-{transcript.stem[:8]}.jsonl"
        target.write_text(cleaned, encoding="utf-8")
        grand_total += count

        # Never ship a transcript the reader's tools cannot open.
        broken = sum(
            1 for line in cleaned.splitlines()
            if line.strip() and not _parses(line)
        )
        status = "ok" if broken == 0 else f"{broken} UNPARSEABLE LINES"
        print(
            f"{transcript.name} → {target}  "
            f"({target.stat().st_size // 1024} KB, {count} redactions, {status})"
        )
        if unparsed:
            print(f"  note: {unparsed} line(s) were not valid JSON in the source")
        if broken:
            raise SystemExit("refusing to ship a corrupted transcript")

    (DEST / "README.md").write_text(README_TEMPLATE.format(redactions=grand_total), encoding="utf-8")

    print(f"\ntotal redactions: {grand_total}")
    print(f"wrote {DEST}/README.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
