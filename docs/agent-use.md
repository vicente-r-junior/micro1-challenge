# Coding-agent use disclosure

The challenge requires coding-agent use and requires disclosing it. This file
lists every agent involved, in both senses: the agents that *built* the project
and the agents that *are* the project.

## Agents that built this project

| Agent | Model | What it did |
|---|---|---|
| Claude Code | Claude Opus | Wrote the harness, the agents, the benchmark cases, the tests and the documentation, in one working session driven by the author. |

The author set the direction and made the engineering calls — most importantly
the decision to throw away the original design (an LLM writing tests for the
LLM's own migration) and rebuild around a differential oracle. Several
corrections in [`CHANGELOG.md`](../CHANGELOG.md) Part 2 came from running the
harness against migrations whose correctness was already known and noticing the
numbers were wrong.

The session transcript is included in `trajectories/build/` as required. It is
copied there by `scripts/prepare_build_trajectory.py`, which redacts anything
shaped like a credential on the way in — a raw session log was never written
with publication in mind, so it is scrubbed rather than trusted. Run it with
`make trajectory`; the file it writes records how many redactions were applied.

## Agents that are the project

Four, all defined in [`src/agents.py`](../src/agents.py). Each one's system
prompt is in the source and reproduced in its trajectory.

| Agent | Tools | Purpose |
|---|---|---|
| **Analyst** | none | Reads the legacy module, writes a migration brief listing the externally observable risks. |
| **Migrator** | none | Writes the FastAPI module from the source, the brief, the AST route inventory and the lessons ledger. |
| **Repair** | `get_probe_detail`, `search_legacy`, `run_differential`, `submit` | Given a behavioural diff, inspects, hypothesises, patches and re-tests. Bounded at 14 turns and 4 differential runs. |
| **Reflector** | none | Turns confirmed failures into general rules for the ledger. |

Notably, **none of them decides whether the migration is correct.** That is
`parity.compare`, which contains no model.

[`agent-in-action.md`](agent-in-action.md) walks through one repair run
turn by turn, including the calls the agent wasted.

## What is in a trajectory

One JSONL file per agent run, under `trajectories/<variant>/<case>.jsonl`.
Records are append-only and flushed on write, so a crashed run still leaves a
readable trace.

| Event | Contents |
|---|---|
| `run_start` | variant, case, model, replay flag |
| `llm_call` | tag, attempt, full system prompt, full user message, full completion, tokens, cost, latency |
| `tool_call` / `tool_result` | tool name, arguments, result |
| `decision` | what the orchestrator did and **why**, with the metrics that drove it |
| `human_checkpoint` | the prompt shown, the answer given, the mode |
| `run_end` | outcome and totals |

Prompts and completions are stored verbatim, not summarised: a reader has to be
able to see exactly what the model was told and exactly what it replied.

Read one as a narrative:

```bash
python src/show_trajectory.py trajectories/v4_memory/case_01_inventory.jsonl
python src/show_trajectory.py trajectories/v4_memory/case_13_restful_todo.jsonl --full
```

That prints each model call with its prompt and reply, every tool call and its
result, and each decision the orchestrator made with the reason and the metrics
behind it. Or read the raw records:

```bash
python - <<'PY'
import json
for line in open("trajectories/v4_memory/case_01_inventory.jsonl"):
    e = json.loads(line)
    print(f"{e['t_rel_s']:7.1f}s  {e['kind']:16s} {e.get('tag') or e.get('tool') or e.get('what','')}")
PY
```
