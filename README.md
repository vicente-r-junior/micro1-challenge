# Does this migration still do what the old one did?

**A Flask→FastAPI migration agent whose verifier is not a language model.**

micro1 Frontier Engineering Challenge 2026 · individual entry

> **There is an interactive version of this page.** Open
> [`docs/index.html`](docs/index.html) in a browser — no server, no build. Its
> measurement grid is live: 212 cells, one per HTTP probe, and switching the
> agent configuration or the model recolours them from the committed results.
> It is the fastest way to see what actually changed.

> **Walkthrough video** — a five-minute tour of the problem, the verifier, and
> one live migration against real third-party code.
> Link: _see the HackerEarth submission form_.

---

## The baseline solution and the advanced solution

The challenge asks for both, and asks that the advanced one be a real
improvement rather than a cosmetic variation. Here they are, named, with the
command that runs each and the measured difference between them.

| | **Baseline solution** | **Advanced solution** |
|---|---|---|
| Name in the code | `v0_baseline` | `v2_repair` |
| What it is | one prompt: the legacy module in, a FastAPI module out | the same migrator, plus a behaviour contract and an autonomous repair loop with four deterministic tools and a differential oracle |
| Run it | `docker compose run --rm reproduce` — the report covers both | same command; both appear in [`results/REPORT.md`](results/REPORT.md) |
| Shippable migrations | **12/16** | **16/16** |
| On real third-party code | **0/2** | **2/2** |
| Cost | $0.27 | $0.73 |

The improvement is not that the second one writes better code. It is the same
migrator with the same model. The difference is that the advanced solution can
**find out that it was wrong** — it replays the legacy application's own
responses against the migration and repairs against the diff — and the baseline
cannot. That is why the column that moves from 0/2 to 2/2 is the third-party
one, on code neither version had seen.

Two further variants, `v3_analyst` and `v4_memory`, were built, measured and
**removed**: they cost 60% more and produced zero additional shippable
migrations. Part 3 of [`CHANGELOG.md`](CHANGELOG.md) records both, with the
evidence.

### Where each required item lives

| Required | Where |
|---|---|
| Complete solution code | this repository; `src/` is 15 modules, all written for this challenge ([`NOTICE.md`](NOTICE.md)) |
| Improvement changelog | [`CHANGELOG.md`](CHANGELOG.md) — 26 entries, each tied to the evidence that forced the next decision, closing with the main failure mode and the hot take |
| Reproduction guide | [`REPRODUCTION.md`](REPRODUCTION.md) — clean environment, exact commands, pinned versions, runtime and cost |
| Agent trajectories | [`trajectories/`](trajectories/) — 243 JSONL runs, every tool call and result, plus the human checkpoints; the coding-agent session that built this is in [`trajectories/build/`](trajectories/build/) |
| Archive | `submission.zip`, built by `make package`, which verifies the archive rather than the working tree |
| Solution video | see above |

### On the rule about consequential actions

The consequential action in this tool is **writing generated code into someone's
source tree**, and it is gated: the run stops, prints the parity result and a
diffstat, and waits for a human. Answer anything but `y` and the file is not
written. That gate is exercised by a test, and every answer is recorded in the
trajectory.

The generated code is also *executed*, to find out what it does. That runs in a
subprocess, in a throwaway directory, under a timeout — enough to contain an
accident, and **not a security boundary**, which
[`src/sandbox.py`](src/sandbox.py) states in full. Every command this README
gives runs inside the container, where the container is the boundary; the one
exception is called out where it appears.

---

---

## The user and the bottleneck

A team is running a Flask service that works. It has been in production for
years, clients depend on it, and everyone agrees it should be on FastAPI —
async, typed, generated OpenAPI, a maintained ecosystem.

They have not migrated. Not because the rewrite is hard: an LLM produces a
clean, idiomatic FastAPI version of any handler in about eight seconds. They
have not migrated because **nobody can prove the new version behaves like the
old one**, and the old one is what the clients were built against.

The regressions that matter are not crashes. They are quiet. Every row below is
a change this project **measured** in a migration a current model actually
produced — none of them is hypothetical:

| What the migration did | What the client sees | Where |
|---|---|---|
| Dropped a route while rewriting the rest | `GET /todos` answered 200 before, **405** after | `case_13` |
| `raise HTTPException(...)` instead of returning the body | `{"detail": ...}` where `{"message": ...}` used to be | `case_13`, `case_14` |
| Modelled the body with Pydantic | **422** for input the old app coerced and accepted with 201 | `case_13` |
| Typed a query parameter | **422** for `?page=not-a-number`, which used to return 200 with data | `case_12` |
| **Fixed a bug** — wrapped an unhandled `KeyError` | a clean **404** where a **500** used to surface | `case_14` |

Read that last row again. The new code is *better*. It is also a different
contract, and every client with retry-on-5xx behaves differently tomorrow.

Every row cites the case it was measured on and can be checked against
[`results/REPORT.md`](results/REPORT.md) and the migrated modules committed
under `results/migrated/v0_baseline/`.

Every one of these passes code review. Every one breaks somebody at 3 a.m. That
is the bottleneck this project attacks: not *writing* the migration, but
**earning the right to merge it**.

## Why the obvious agent design fails

The natural way to build this is: migrate with an LLM, then ask an LLM to write
tests for the result, then run them.

That verifier is worthless, and worse than worthless, because it is confident.
The tests are generated **from the migrated code**, so they encode whatever the
migration decided. If the migration changed `{"error": ...}` to
`{"detail": ...}`, the generated test asserts `detail`. Green.

**A model cannot be the oracle for its own output.** The specification has to
come from somewhere the model does not control — and here it already exists: the
legacy application itself.

This project started as exactly the design above. It is preserved, with the full
reasoning for abandoning it, in [`docs/superseded/`](docs/superseded/).

## How it works

```
legacy_app.py (Flask)
        │
        ├─ 1. AST route extraction ──────────► routes, body keys, query types
        │      no model runs here                (probing.py)
        │
        ├─ 2. deterministic probe synthesis ─► 212 HTTP requests over 16 cases
        │      happy · missing_field · bad_type · malformed_json
        │      absent_id · wrong_method · bad_query_type · unauthenticated
        │
        ├─ 3. replay against the ORIGINAL ───► THE CONTRACT
        │      Flask test client, sandboxed      (this is the specification)
        │
        │   ┌──────────── the agentic part ────────────┐
        ├──►│  Analyst   → migration brief             │
        │   │  Migrator  → FastAPI module              │
        │   │  Repair    → tool loop, budgeted         │
        │   └──────────────────────────────────────────┘
        │
        ├─ 4. replay the SAME probes ────────► observed behaviour
        │      against the migrated app
        │
        ├─ 5. diff ──────────────────────────► behavioural parity %
        │      status + normalised body           (parity.py)
        │      failures become the repair agent's feedback
        │
        └─ 6. human checkpoint ──────────────► nothing is written until approved
```

Steps 1, 2, 3, 5 contain no model at all. That is the design.

## The agent

Six levers, six purposeful choices. Five were isolated by the ablation below;
the sixth, cross-case memory, **could not be** — the repair loop clears the
failures its ledger would have learned from, so `v4` reproduced `v3` byte for
byte and the component was removed. Each is documented in
[`CHANGELOG.md`](CHANGELOG.md), including that one.

| Lever | Component | What it does |
|---|---|---|
| Specialised skills | **Analyst agent** | reads the legacy module and writes a risk brief: which Flask idioms are present and which are observable from outside |
| Better context | **Migrator agent** | receives the brief, the AST route inventory and the lessons ledger — not just raw source |
| Better tools | **4 deterministic tools** | `get_probe_detail`, `search_legacy`, `run_differential`, `submit` |
| Verification | **Differential oracle** | the legacy app's own responses; no model votes on correctness |
| Memory | **Lesson ledger** | confirmed failures on earlier cases become rules injected into later ones |
| Orchestration | **Repair agent** | an autonomous tool loop, bounded at 8 turns and 3 differential runs |

The repair agent is the only one with tools, and it decides what to look at. It
can pull up a single probe to see exactly what was sent and what each side
answered, grep the original source to check what the handler really does, and
test a candidate before committing to it.

**[`docs/agent-in-action.md`](docs/agent-in-action.md) walks through one real
repair, turn by turn**, on third-party code: the agent reads three failing
probes, greps the legacy module for the error strings, gets nothing back three
times, works out that the envelope belongs to the framework rather than the
application, writes a candidate and tests it — reaching full parity on the first
try. Along the way it deliberately puts back a `500` that the baseline migration
had "fixed" into a `404`, because the oracle says 500.

## "Isn't this just a better prompt?"

A fair question, and the reason the results are an ablation rather than a single
before-and-after. Each row turns on exactly one more component than the row
above it, over the same cases with the same model:

| | What is switched on |
|---|---|
| `v0_baseline` | one direct prompt — the honest starting point |
| `v1_contract` | the behaviour-preservation prompt, and scoring against the recorded contract. **No repair.** This row is the prompt, and only the prompt. |
| `v2_repair` | the tool-calling repair loop |
| `v3_analyst` | the analyst brief in the migrator's context |
| `v4_memory` | the cross-case lesson ledger |

If `v1` captured most of the gain, the honest conclusion would be that this is a
prompt with extra steps, and the table would say so. The numbers below are what
they are.

Two things a prompt cannot do at all, and they matter more than the ranking:
the harness **tells you which migrations are wrong**, and it does so without
asking a model. A prompt improves the odds. It never tells you whether you got
lucky this time.

## Results

16 cases · 212 probes · `deepseek/deepseek-v4-flash` · full table in
[`results/REPORT.md`](results/REPORT.md), reproducible offline with
`make reproduce`.

**Shippable** = every probe reproduces the legacy status *and* body. It is the
only bar that matters, because you do not deploy 92% of a service.

| Variant | Shippable | Mean parity | Calls | Cost | Model time |
|---|---|---|---|---|---|
| `v0_baseline` one prompt | 12/16 | 90.7% | 16 | $0.27 | 23 min |
| `v1_contract` + behaviour prompt | 14/16 | 96.5% | 16 | $0.68 | 67 min |
| **`v2_repair` + tool loop** | **16/16** | **100%** | 25 | $0.73 | 71 min |
| `v3_analyst` + brief | 16/16 | 100% | 40 | $1.17 | 109 min |
| `v4_memory` + ledger | 16/16 | 100% | 40 | $1.17 | 109 min |

**Three of those five rows tie at 16/16.** That is a real finding — the last two
components bought nothing, and Part 3 of the changelog says so with the cost
attached — but it also means this table understates the range the agent covers.
The five-model table further down is where the spread actually lives.

### What the 212 probes are made of

A reviewer should know the shape of the denominator before reading a percentage,
so here it is.

| Probe kind | Count | Share |
|---|---|---|
| `happy` | 57 | 26.9% |
| `wrong_method` | 45 | 21.2% |
| `absent_id` | 42 | 19.8% |
| `missing_field` | 18 | 8.5% |
| `bad_type` | 18 | 8.5% |
| `malformed_json` | 18 | 8.5% |
| `unauthenticated` | 10 | 4.7% |
| `bad_query_type` | 4 | 1.9% |

Two things follow that work against the headline number, and both are worth
saying out loud rather than leaving in the code.

**41% of the set is `wrong_method` and `absent_id`** — the two classes cheapest
to get right, because they mostly ask the framework to reject a request rather
than asking the application to compute an answer.

**26% of probes (55 of 212) are scored on their status code alone.** Those are
the ones where the legacy app replied with Flask's own HTML error page. The
exemption is deliberately narrow — `src/parity.py::_body_is_application_output`
requires a 4xx/5xx status *and* an HTML content type, so a CSV export, a
plain-text response and an HTML page served with a 200 are all compared in full.
It was wider once: an earlier version relaxed the check for *any* non-JSON body
and quietly stopped comparing 8 of 13 probes on one case. That is recorded as
H13 in [`CHANGELOG.md`](CHANGELOG.md).

So "100% parity" means: every probe reproduced the legacy status, and every
probe whose body the legacy app actually authored reproduced that body too. It
does not mean the tool reproduced Flask's error markup, which no FastAPI
migration can or should.

### The result that changed the project

Split the same run by where the code came from:

| Variant | Synthetic — 14 cases **I wrote** | Third-party — 2 cases **I did not** |
|---|---|---|
| `v0_baseline` | 12/14 | **0/2** |
| `v1_contract` | 14/14 | 0/2 |
| `v2_repair` | 14/14 | **2/2** |

I designed fourteen migration traps and a current model walked through twelve of
them. Then a hundred and twenty-two lines of ordinary flask-restful code, aimed at nothing in
particular, and it failed both.

**A benchmark written by the author of the tool measures the author's
imagination.** The third-party column is the one worth reading, and two cases is
a small sample — [`docs/benchmark-design.md`](docs/benchmark-design.md) says so
at length, including why real Flask modules are so hard to obtain (most of them
cannot be executed in isolation).

The repair loop is what closed that column: `case_13` 59% → 76% → **100%**,
`case_14` 33% → 67% → **100%**, in five and four turns with one differential run
each.

### Five models, two vendors, three generations

The obvious objection is that a better model would not need any of this. So the
baseline and the repair loop were run again on four more models, over the same
sixteen cases, through the same harness, with the same code. Reports under
`results/`.

| Model | Baseline | &hellip; that start and lie | Baseline on real code | With repair | Real, with repair |
|---|---|---|---|---|---|
| `gpt-4o-mini` (2024) | 1/16 | 12 | **0/2** | 5/16 | 0/2 |
| `gpt-5.4-mini` | 3/16 | 11 | **0/2** | 11/16 | 1/2 |
| `gpt-5.5` | 11/16 | 3 | **0/2** | **16/16** | **2/2** |
| `deepseek-v4-flash` | 12/16 | 4 | **0/2** | **16/16** | **2/2** |
| `deepseek-v4-pro` (reasoning) | 10/16 | 6 | **0/2** | **16/16** | **2/2** |

**Not one model, from either vendor, in any generation, got a single piece of
real third-party code right on its own.**

Three things fall out of that, and none of them is "use a better model".

**Capability does not predict safety.** Across the five, the baseline moved
between 1 and 12 out of 16 without the third-party column ever leaving zero. The
reasoning model did not beat the fast model it costs three times as much as.

*What that deliberately does not say* is that the cheaper model is better — see
the replication below, where the ordering reverses.

**Most failures are not crashes.** The third column counts migrations that
imported cleanly, served every route, answered every request — and answered
differently. Across the five baselines that is **36 migrations**. On the two
DeepSeek models it is *every single failure*: nothing there would have been
caught by checking that the app boots, which is the only check most teams
actually run.

**Verification amplifies capability; it does not replace it.** The repair loop
improved all five, but reached 16/16 only on models strong enough to act on a
diff. `gpt-4o-mini` emits Pydantic v1 `__root__` and unterminated f-strings;
being told precisely what is wrong does not make it able to fix it. An oracle
tells you the truth about your migration — it cannot write the migration for
you.

### Running the same model twice

A single run of a non-deterministic system is one sample, so two of the models
were run again from scratch on identical input.

| Model | Sample 1 | Sample 2 | Cases that changed verdict |
|---|---|---|---|
| `deepseek-v4-flash` | 10/14 | **8/14** | `case_01`, `case_02` |
| `deepseek-v4-pro` | 10/16 | **11/16** | `case_02`, `case_05`, `case_08` |

*(Compared over the cases that completed in both samples; two `flash` calls hit
an API timeout in sample 2 and are excluded rather than scored as failures.)*

**On denominators, because they are the easiest place to flatter a result.** A
run can fail two ways and they are not the same failure. If the model returns no
code, or code that will not parse or import, the model failed at the task: that
is a migration nobody can ship, and it is counted — `gpt-4o-mini` is reported
above as **1/16** and **5/16**, not 1/14 and 5/15, and the three cases where it
returned no code at all are three of those losses. If instead the *provider*
timed out, nothing about the model was measured, and scoring a zero would report
an infrastructure problem as a capability problem; those are excluded, and the
sentence above says so. The per-run files under `results/` are the raw output of
the harness and use its narrower internal denominator, which is why
`results/cross_vendor/REPORT.md` prints 1/14 where this table prints 1/16. Every
row's `cases`, `scored` and `failed_to_run` are in the matching `summary.json`,
so the arithmetic is checkable either way.

The synthetic score moves by up to three cases between identical runs, and the
ordering between the two DeepSeek models **reverses** — the "stronger model did
worse" reading from the first sample does not survive the second. That is why
nothing in this project ranks models by baseline.

What did not move:

> **Seven baseline runs. Five models. Two vendors. Thirteen scored attempts at
> real third-party code. Zero passed.**

Across those same seven runs the synthetic baseline ranged from 1 to 12 out of
16. The noise is entirely in the column I built myself. The column I did not
build never moved.

**Why these five.** Two vendors, and within OpenAI a deliberate spread across
generations: a small 2024 model, a current small one, and a current strong one.
`gpt-5.6-sol` was excluded on purpose — its chat endpoint cannot use function
tools without disabling reasoning, and comparing a crippled configuration
against the others would not be like for like.

### Two components were removed

`v3_analyst` and `v4_memory` cost **+60% and +53% more** in money and model time
for **zero** additional shippable migrations. Both were built, measured, and
cut; both stay in the repository behind `--variants all` because the ablation
showing they do not pay is part of the evidence. The reasoning, including the
caveat that no component can show a gain once the one before it reaches 100%, is
in [`CHANGELOG.md`](CHANGELOG.md#part-3--what-was-removed).

## How to verify this — two paths

The point of the whole project is that a claim should be checkable. So this one
is too, and there are two ways to do it depending on how much you want to spend.

### Start here

Docker is the only prerequisite. Three lines, from nothing:

```bash
git clone https://github.com/vicente-r-junior/micro1-challenge.git
cd micro1-challenge
docker compose run --rm reproduce
```

That prints the results table in well under a minute — 23 s of work, about 40 s
through Docker on a laptop — with **no API key and no network access**. It must match [`results/REPORT.md`](results/REPORT.md)
exactly — the file is committed, so **`git diff` after the run comes back
empty**. Both results files are byte-deterministic: run it twice and you get
identical bytes.

The replay writes its trajectories to `/tmp` rather than over the committed
ones, so checking the numbers never destroys the record of the runs that
produced them.

Prefer a zip? [Download it here](https://github.com/vicente-r-junior/micro1-challenge/archive/refs/heads/main.zip), unzip, and
run the same command from inside the folder.

### Path A — without any AI at all

**No API key. No network. No cost. Under a minute of wall-clock.**

Everything that decides correctness in this project is deterministic, so all of
it can be checked with the models switched off entirely.

```bash
docker compose run --rm test        # 49 tests, ~12s
docker compose run --rm reproduce   # the full benchmark, ~40s
```

The first command exercises the parts that no model touches: route extraction
from all three Flask registration styles, probe determinism, the oracle catching
an `{"error": …}` → `{"detail": …}` rewrite, the human approval gate blocking a
write, the CLI refusing to overwrite its own source.

The second replays the entire five-variant ablation from
[`data/llm_cache.jsonl`](data/llm_cache.jsonl), a file of recorded model
responses committed with the repository, and must print the same table as
[`results/REPORT.md`](results/REPORT.md).

**Why a cache instead of just calling the models?** Because these models are not
deterministic, even at temperature 0. A live re-run produces *different* numbers,
so nobody could ever check the ones reported here. Recording every request makes
the result auditable — and it turns four dollars and six hours of model time
into sixteen seconds.

**It cannot cheat.** A prompt that is not in the cache raises `CacheMiss` and
stops the run. A missing entry can never be silently skipped and scored as a
pass, so if the run completes, every figure came from the committed cache.

Want to see it work rather than take my word for it? Corrupt the cache and watch
it refuse:

```bash
cp data/llm_cache.jsonl /tmp/backup && head -5 data/llm_cache.jsonl > data/llm_cache.jsonl
make reproduce                       # CacheMiss, non-zero exit
cp /tmp/backup data/llm_cache.jsonl
```

### Path B — with AI, live

**Needs a provider key. Costs about $4 for the whole ablation.**

```bash
cp .env.example .env       # then put a key in it; .env is git-ignored
make record                # re-runs everything live and rewrites the report
```

The numbers will not match the committed ones exactly, and that is the expected
result rather than a bug — it is the reason Path A exists. What should hold is
the *shape*: the baseline failing the third-party cases, the repair loop closing
them.

The model is one string, so any provider works:

| Provider | `MIGRATION_MODEL` | Key variable |
|---|---|---|
| DeepSeek | `deepseek/deepseek-v4-flash` | `DEEPSEEK_API_KEY` |
| DeepSeek (reasoning) | `deepseek/deepseek-v4-pro` | `DEEPSEEK_API_KEY` |
| OpenAI | `openai/gpt-4o-mini` | `OPENAI_API_KEY` |
| Anthropic | `anthropic/claude-sonnet-4-5` | `ANTHROPIC_API_KEY` |
| Anything OpenAI-compatible | `openai/<name>` + `MIGRATION_API_BASE` | `OPENAI_API_KEY` |

To watch a single migration happen, with the human approval gate on:

```bash
python src/migrate.py data/cases/case_01_inventory/legacy_app.py
```

> **This runs model-written code on your machine.** The harness executes both
> applications in a subprocess, in a throwaway directory, under a timeout — that
> contains an accident, not an attacker. It is not a security boundary and
> `src/sandbox.py` says so in full. Every other command in this README runs
> inside the container, where the container is the boundary; this one does not.
> Prefer `docker compose run --rm demo` unless you have a reason.

It prints the parity result and a diff summary, then asks before writing
anything. Answer `n` and **the migration is not written** — the run's own
trajectory is still recorded, because a rejected migration is a result worth
keeping, but no generated code reaches your source tree.

### Without Docker

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make test && make reproduce
```

Python 3.11 or newer. Full setup, versions, costs and troubleshooting:
[`REPRODUCTION.md`](REPRODUCTION.md).

## Using it on your own code

```bash
python src/migrate.py path/to/your_flask_app.py
```

Three artefacts land next to your file: the migrated module, a
`_MIGRATION_REPORT.md` listing every difference a client would observe, and the
full agent trajectory. Nothing is written until you approve it, and the tool
refuses outright to write over the file it read.

## Honest limitations

- **Only two of the sixteen cases are third-party code.** The other fourteen were
  written for this benchmark, each aimed at specific migration traps. That is
  a deliberate trade — they run offline and cover traps a random sample would
  miss — but it does mean the benchmark was designed by the same person who
  designed the tool. `docs/hard-case.md` reports what happened on code that was
  not.
- **The probe set is derived, not exhaustive.** It covers the parameters the
  handler visibly reads. A key assembled dynamically is missed, and a missed key
  costs coverage — it can never turn a failing migration into a passing one, but
  it can leave a real regression unmeasured.
- **The module must be executable in isolation.** A blueprint that imports a
  database layer and six internal modules cannot be replayed, so it cannot be
  scored. This is the honest boundary of the approach and it is where most real
  legacy code lives. See `docs/hard-case.md`.
- **Side effects are not modelled.** Probes are replayed against in-process
  state. A handler that writes to a database is only compared on its response.
- **Fixtures are declared, not discovered.** The harness cannot guess a valid
  auth token or an existing record id, so each case supplies them — exactly as
  an integration test would.

## Main failure mode

**The oracle has to run the legacy application, and most real Flask code cannot
be run in isolation.**

Pointed at `app/case/case_misp.py` from flowintel — 1017 lines, 39 routes — the
static half worked perfectly and produced 171 probes. Then it recorded exactly
zero responses, because the module imports `flask_login` and five sibling
packages and expects a live database session. It is not a program; it is a
fragment of one, and no amount of engineering makes a fragment answer HTTP.

Stubbing those imports would mean guessing what the dependencies do, and a
guessed oracle is the exact failure this project exists to avoid. So the honest
statement is that **this approach is strongest where migration is already
easiest**, and weakest on the tangled modules that are the actual reason teams
stay on Flask. [`docs/hard-case.md`](docs/hard-case.md) reports it in full,
along with the version worth building next: probe a *running* service over HTTP
rather than an imported module — same oracle, same metric, no import problem.

A second, smaller one, visible in the trajectories: the repair agent
over-inspects. On `case_13` it burned five of eight turns and eighteen probe
lookups before writing a line of code, and invented a probe id that does not
exist. Exploration is cheap and feels productive, so a budget spent on it is a
budget spent on nothing.

## Hot take

**LLM-generated tests do not verify an LLM's output — they launder it.**

The test generator and the code generator share the same misreading of the
requirement, so the test encodes the bug as the expectation and reports green.
This is strictly worse than having no verification, because no verification
leaves you appropriately nervous, while a passing suite makes you merge.

The corollary is the design rule this whole project is built on: **an agent's
verifier must draw its ground truth from something the agent cannot influence.**
For a migration, that is the system being replaced — it is running, it is
authoritative, and it will answer every question you ask it. Most "agentic
verification" I see asks the model to check itself in a different font.

## Agent trajectories

Every model call — prompt, completion, tokens, cost, latency, and every tool
call and its result — is written to JSONL under `trajectories/`. Disclosed
coding-agent use is documented in [`docs/agent-use.md`](docs/agent-use.md).

## Author

**Vicente Jr** — built this for the micro1 Frontier Engineering Challenge 2026.

- GitHub — [vicente-r-junior](https://github.com/vicente-r-junior)
- LinkedIn — [vicente-r-junior](https://www.linkedin.com/in/vicente-r-junior/)
- Repository — [github.com/vicente-r-junior/micro1-challenge](https://github.com/vicente-r-junior/micro1-challenge)

## Licence

MIT. Provenance and third-party attribution: [`NOTICE.md`](NOTICE.md).
