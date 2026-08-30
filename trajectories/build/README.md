# Build trajectory — the session that produced this project

`claude-code-session-62fa5efb.jsonl` is the complete, unedited session log of
the coding agent used to build this submission, disclosed under the challenge's
agent-use requirement and described in [`docs/agent-use.md`](../../docs/agent-use.md).

Credentials and token-shaped strings were redacted by
[`scripts/prepare_build_trajectory.py`](../../scripts/prepare_build_trajectory.py)
before the file was copied here. The script re-parses everything it writes and
refuses to ship a transcript that no longer decodes (43 redactions applied), so the file is valid JSONL.

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
jq -r 'select(.type=="user") | .message.content | strings'    claude-code-session-62fa5efb.jsonl | head -60
```


The agents that *are* the project have their own trajectories, in English, under
`trajectories/v0_baseline/` through `trajectories/v4_memory/`, plus the
cross-model runs. Render any of them:

```bash
python src/show_trajectory.py trajectories/v2_repair/case_14_restful_todo_simple.jsonl --compact
```
