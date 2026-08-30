# Reproduction guide

Written for someone starting from a clean machine with nothing installed but
Docker. The headline result reproduces **offline, with no API key and no
network access at run time**.

---

## The one command

```bash
git clone https://github.com/vicente-r-junior/micro1-challenge.git
cd micro1-challenge
docker compose run --rm reproduce
```

Docker is the only prerequisite. Or [download the zip](https://github.com/vicente-r-junior/micro1-challenge/archive/refs/heads/main.zip)
and run the same command from inside the folder.

That builds the image, replays the entire benchmark from the response cache
committed in `data/llm_cache.jsonl`, and prints the results table. It must match
[`results/REPORT.md`](results/REPORT.md) exactly. No key is required and none is
read.

**Why a cache and not a live run?** These models are not deterministic even at
temperature 0. A live re-run produces *different* numbers, so a reader could
never check the ones reported here. Every request is therefore hashed and its
response stored; `--replay` walks the identical sequence of calls, including
every turn of the repair agent's tool loop. A prompt that is not in the cache
raises `CacheMiss` and stops the run — a missing entry can never be silently
skipped and scored as a pass.

## Without Docker

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make reproduce
```

Requires Python 3.11 or newer.

## What you should see

```
model=deepseek/deepseek-v4-flash  cases=16  variants=v0_baseline,…  REPLAY (offline)
  [v0_baseline] case_01_inventory              PASS  (15/15 probes)
  [v0_baseline] case_13_restful_todo            59%  (10/17 probes)
  [v0_baseline] case_14_restful_todo_simple     33%  (3/9 probes)
  …
| Variant | What it adds | Shippable | Mean parity | LLM calls | Cost | Wall |
```

Followed by a per-case table and a split between the synthetic cases and the
third-party ones. The same content is written to `results/REPORT.md` and
`results/summary.json`; both are committed, and the run must reproduce them.

A replayed run finishes in seconds and costs nothing. The wall-clock and cost
columns report what the *original* recording took, not what the replay took —
a replay that claimed to be free would be describing the cache, not the work.

## Verifying the harness itself before trusting its numbers

```bash
docker compose run --rm test        # or: make test
```

48 tests, no model involved. They cover the parts that decide correctness:

- route extraction from decorators **and** from `add_url_rule` + `MethodView`
- probe determinism, and that the 405 probe never hits a sibling handler
- the oracle catching an `{"error": …}` → `{"detail": …}` rewrite
- 400 → 422 being counted as a failure in the headline metric but reported
  separately as a known class
- framework error pages compared on status only
- the human checkpoint blocking the write until approval
- the CLI refusing to write a migration over its own source file
- Flask-RESTful `add_resource` and `reqparse`, and form-encoded probes
- replay answering from cache, and failing loudly on an unseen prompt

## Running the agent live against a provider

Not needed to reproduce the results. Costs money.

```bash
cp .env.example .env          # then put your key in it; .env is git-ignored
make record                   # re-records the cache and the report
```

The model string selects the provider through LiteLLM:

| Provider | `MIGRATION_MODEL` | Key variable |
|---|---|---|
| DeepSeek | `deepseek/deepseek-v4-pro` | `DEEPSEEK_API_KEY` |
| OpenAI | `openai/gpt-4o-mini` | `OPENAI_API_KEY` |
| Anthropic | `anthropic/claude-sonnet-4-5` | `ANTHROPIC_API_KEY` |
| Any OpenAI-compatible | `openai/<name>` + `MIGRATION_API_BASE` | `OPENAI_API_KEY` |

## Using the tool on your own Flask file

```bash
python src/migrate.py path/to/your_app.py
```

Prints the parity result and a unified diff, then asks before writing anything.
`--yes` skips the prompt for CI; `--dry-run` never writes. Produces the migrated
module, a `_MIGRATION_REPORT.md` for the pull request, and a JSONL trajectory.

## What data is required

Nothing external. The fifteen tier-A cases are committed under `data/cases/` and
run offline.

The one tier-B case is **not** committed: it is a real AGPL-3.0 file from the
flowintel project, and redistributing it would put this repository under that
licence. Fetch it explicitly if you want to reproduce the analysis in
[`docs/hard-case.md`](docs/hard-case.md):

```bash
python data/cases/case_99_flowintel_misp/fetch.py    # needs network
```

## Versions, runtime and cost

| | |
|---|---|
| Python | 3.12 (image: `python:3.12-slim`; 3.11+ works) |
| Flask | 3.1.x — executes the legacy apps to record the contract |
| Flask-RESTful | 0.3.x — two benchmark cases are real Flask-RESTful modules |
| FastAPI | 0.135.x — executes the migrated apps |
| LiteLLM | 1.89.x — provider routing |
| Model behind the committed cache | `deepseek/deepseek-v4-flash` |

### What each path costs

| | Calls | Cost | Model time | Wall clock |
|---|---|---|---|---|
| **`make reproduce` — what a judge runs** | 0 | **$0.00** | — | **23 s** |
| `make test` | 0 | $0.00 | — | 8 s |
| Live re-record of the whole ablation | 137 | **$4.02** | 379 min | ~95 min at 4 workers |

Twenty-three seconds against six hours of model time, for the same table. That
gap is the entire argument for shipping the cache: without it, checking the
reported numbers means spending four dollars and an evening, so nobody checks
them. Both wall-clock figures are the work itself; going through Docker on a
laptop roughly doubles them, which is still under a minute.

The live figures come from the run that produced
[`results/REPORT.md`](results/REPORT.md): 270,396 prompt tokens and 3,006,130
completion tokens. The output count is far larger than the input because the
model behind the cache is a reasoning model — most of those tokens are thinking,
not code.

Every number in this table is measured, not estimated.

## If something goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `CacheMiss` on the first prompt | you passed `--model` with something the cache was not recorded against | drop `--model`; on `--replay` it defaults to the model recorded in the cache |
| `CacheMiss` partway through | the cache does not cover that case, usually because a case was added after it was recorded | `make record` with a provider key |
| `No module named flask` | dependencies not installed | `pip install -r requirements.txt`, or use Docker |
| A case scores 0% with `app_imports: false` | the generated module imports something the environment lacks | check `requirements.txt`; `uvicorn` and `python-multipart` are pinned for exactly this reason |
| A case reports `legacy app failed to run` | the legacy module cannot be imported standalone | that is tier B by definition; see [`docs/hard-case.md`](docs/hard-case.md) |
| Sandbox timeout | slow machine, or a generated module that blocks on import | raise `--timeout`; the default is 90 s per replay |
| Numbers differ from `results/REPORT.md` | you ran without `--replay`, so the models were called live | these models are not deterministic at temperature 0; only the replay reproduces |

### A receipt for the cache

The cache is the obvious place to fake a result, so here is a live call placed
beside its committed entry. Same case, same prompt, cache bypassed, real
provider, on 2026-08-30:

```
prompt key   462092221395ca89253eec34383e46a1…   identical on both sides

                         committed cache     live call
model                 deepseek/deepseek-v4-flash        (same)
prompt tokens                        661           661
completion tokens                  24218         25922
cost (USD)                        0.0320        0.0342
latency (s)                        151.7         161.0
behavioural parity                  100%           87%
```

Read the rows in order:

- **661 prompt tokens on both sides.** The committed entry was produced by this
  exact prompt, byte for byte — which is also why the key matches.
- **24,218 against 25,922 completion tokens.** The model is not deterministic,
  which is the entire reason a cache exists. A second live call, made minutes
  apart, returned 19,342 — three runs, three lengths.
- **100% against 87% parity.** The live migration came out *worse* than the
  recorded one, and both live calls landed on the same 87%. Numbers move between
  runs; removing that movement is what the replay is for, and it is why every
  figure in this repository comes from a fixed recording rather than from
  whatever the model produces today.

What this does **not** prove: that all 344 entries across the seven committed
cache files came from a provider. Nothing short of a signed response would,
and no provider signs them. What it establishes is that the entries are keyed
by real prompts, that their metadata is consistent with a real call, and that
a missing entry stops the run instead of being silently skipped.

### A note on trust

`--replay` fails loudly on a prompt it has never seen rather than skipping it.
That is deliberate: a cache that silently ignored a missing entry would let a
run report a number computed from a subset of the work, which is worse than no
number. If the run completes, every model call in the reported figures came
from the committed cache.
