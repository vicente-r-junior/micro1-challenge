# Improvement changelog

Every entry records what was tried, what the evidence said, and what was decided.
Numbers come from `results/REPORT.md`; nothing here is asserted without a run
behind it.

The primary metric throughout is **behavioural parity (strict)**: the share of
probes on which the migrated FastAPI app returns the same HTTP status *and* the
same response body as the legacy Flask app. The legacy app is the oracle.

---

## Part 1 — how the solution evolved

All figures from [`results/REPORT.md`](results/REPORT.md), reproducible with
`make reproduce`. Every variant runs the same 16 cases with the same model
(`deepseek/deepseek-v4-flash`) through the same harness, and each adds exactly
one component to the one above it.

**Shippable** means every probe reproduces the legacy status *and* body. It is
the only bar that matters: you do not deploy 92% of a service.

| Stage | Shippable | Real code | Mean parity | Calls | Cost | Model time |
|---|---|---|---|---|---|---|
| **V-1** discarded before measuring | — | — | — | — | — | — |
| **V0** one direct prompt | 12/16 | **0/2** | 90.7% | 16 | $0.27 | 23 min |
| **V1** + behaviour-preservation prompt | 14/16 | 0/2 | 96.5% | 16 | $0.68 | 67 min |
| **V2** + tool-calling repair loop | **16/16** | **2/2** | 100% | 25 | $0.73 | 71 min |
| **V3** + analyst brief | 16/16 | 2/2 | 100% | 40 | $1.17 | 109 min |
| **V4** + cross-case memory | 16/16 | 2/2 | 100% | 40 | $1.17 | 109 min |

---

### V-1 — an LLM writing tests for the LLM's own migration

**Tried.** The project's original design, written before any benchmark existed:
migrate with a model, ask a second call to write a `TestClient` suite **for the
code the first call produced**, run it in a sandbox, feed tracebacks back for a
retry. Preserved in full at [`docs/superseded/`](docs/superseded/).

**Evidence.** None, deliberately. The defect is structural, not statistical: the
test is generated from the migrated code, so it asserts whatever the migration
decided. When the migration rewrites `{"error": …}` into `{"detail": …}`, the
generated test asserts `detail` and reports green. Measuring it would have
produced a pass rate that meant nothing.

**Decision.** Thrown away. The oracle had to come from somewhere the model could
not influence, and it already existed: the legacy application is running, it is
authoritative, and it will answer any request you send it.

### V0 — the baseline: one direct prompt

**Tried.** "Migrate this Flask application to FastAPI." No contract, no
verification, no retry. This is what a competent engineer does with an LLM
today, and the challenge asks the baseline to be exactly that.

**Evidence.** **12/16 shippable, mean parity 90.7%, $0.27, 16 calls.**

And the split that reframed the project: **12/14 on the synthetic cases I wrote,
0/2 on the real third-party code I did not.** Fourteen traps I designed and
anticipated — the model walked through twelve. Two hundred lines of ordinary
flask-restful code aimed at nothing in particular — it failed both, by dropping
a route (`GET /todos`: 200 → 405), rewriting every error envelope, tightening
validation the original left loose, and *fixing a bug* (`500` → `404`).

**Decision.** Two things followed. The third-party column became the number to
watch, and the framing changed: the problem is not that the model is unreliable,
it is that the model is reliably **almost** right — which is exactly the
condition under which people stop checking.

### V1 — record the contract, and tell the migrator what it is for

**Tried.** Execute the legacy app first, record its response to every probe, and
score against that. The migrator's instructions change accordingly: preserve
status codes exactly, preserve error bodies verbatim rather than raising
`HTTPException`, keep lenient input handling lenient. No repair loop yet — this
row isolates the prompt.

**Evidence.** **14/16, mean 96.5%.** `case_05_response_shapes` 85% → 100% and
`case_12_pagination_headers` 75% → 100%. Both real cases improved but neither
crossed the line: `case_13` 59% → 76%, `case_14` 33% → 67%.

**Decision.** Kept. It is the cheapest gain in the table — same 16 calls, +2
shippable — and it answers the obvious objection honestly: a better prompt gets
you most of the *synthetic* way and none of the *real* way.

### V2 — hand the agent the diff and some tools

**Tried.** When the differential fails, give an agent the behavioural diff (not
a traceback) plus four tools: inspect one probe in full, grep the legacy source,
run the differential on a candidate, submit. Budget: 8 turns, 3 differential
runs.

**Evidence.** **16/16 shippable. Both real cases reached full parity** —
`case_13` 76% → 100% in 5 turns, `case_14` 67% → 100% in 4 turns, one
differential run each. Cost rose from $0.68 to $0.73, calls from 16 to 25:
the loop only engages on cases that need it, which was 2 of 16.

The trajectory is worth reading rather than summarising —
[`docs/agent-in-action.md`](docs/agent-in-action.md) walks through
`case_14` turn by turn. The agent inspected three probes, grepped the module for
the error strings and got **nothing back three times**, concluded the envelope
belonged to `Api(app)` rather than to the application, and wrote a handler
reproducing it. Including putting back a `500` the baseline had "fixed" into a
`404`.

**Decision.** Kept. This is the component that does the work.

### V3 — an analyst brief before any code is written

**Tried.** A separate pass reads the legacy module and writes a risk brief —
which Flask idioms are present, which are externally observable — and the
migrator gets it alongside the source.

**Evidence.** **16/16. Identical to V2 on every case.** Calls 25 → 40, cost
$0.73 → $1.17 (+60%), model time 71 → 109 minutes (+53%). The briefs themselves
are good; they are simply redundant once the repair loop exists, because the
loop finds the same problems empirically and only pays when there is a problem
to find.

**Decision.** **Removed.** See Part 3.

### V4 — cross-case memory

**Tried.** After each case, distil the *confirmed* failures into general rules
and inject the most frequent into later migrations.

**Evidence.** **16/16, and byte-identical to V3** — same 40 calls, same $1.1683,
same model time. The ledger finished with **0 lessons**, and the reason is the
component working exactly as designed: lessons are only written from failures
that survived repair, and V2 had already eliminated all of them. With nothing
learned, the migrator prompt was unchanged, so every call was a cache hit of
V3's.

**Decision.** **Removed.** See Part 3.

### Cross-model check — is this just a weak model?

**Tried.** Run `v0_baseline` and `v2_repair` on four more models, over the same
16 cases, through the same harness, with the same code. Reports under
`results/`.

| Model | Baseline | … that start and lie | Baseline, real code | With repair | Real, with repair |
|---|---|---|---|---|---|
| `gpt-4o-mini` (2024) | 1/16 | 12 | **0/2** | 5/16 | 0/2 |
| `gpt-5.4-mini` | 3/16 | 11 | **0/2** | 11/16 | 1/2 |
| `gpt-5.5` | 11/16 | 3 | **0/2** | **16/16** | **2/2** |
| `deepseek-v4-flash` | 12/16 | 4 | **0/2** | **16/16** | **2/2** |
| `deepseek-v4-pro` | 10/16 | 6 | **0/2** | **16/16** | **2/2** |

**Evidence.** Not one model, from either vendor, in any generation, got a single
piece of real third-party code right on its own.

The third column is the one worth staring at: migrations that imported cleanly,
served every route and answered differently. **36 across the five baselines.**
On both DeepSeek models that is *every* failure — none would have been caught by
checking that the app starts, which is the only check most teams run.

**Decision.** Reported prominently. It removes the most obvious objection to the
project: the model is the part that changes, the oracle is the part that does
not.

It also produced an honest limit. The repair loop improved all five but reached
16/16 only on models strong enough to act on a diff. `gpt-4o-mini` emits
Pydantic v1 `__root__` and unterminated f-strings; telling it precisely what is
wrong does not make it able to fix it. **Verification amplifies capability, it
does not substitute for it.**

**What this evidence does NOT support — measured, not assumed.** Two models were
re-run from scratch on identical input to find out how much a single sample is
worth.

| Model | Sample 1 | Sample 2 | Verdicts that changed |
|---|---|---|---|
| `deepseek-v4-flash` | 10/14 | 8/14 | `case_01`, `case_02` |
| `deepseek-v4-pro` | 10/16 | 11/16 | `case_02`, `case_05`, `case_08` |

The synthetic score moves by up to three cases, and **the ordering between the
two models reverses**. The first sample's "the reasoning model did worse" does
not survive the second. Nothing here ranks models by baseline, and this table is
why.

What survives every sample:

> Seven baseline runs, five models, two vendors, **thirteen scored attempts at
> real third-party code, zero passed** — while the synthetic baseline ranged
> from 1 to 12 out of 16 across the same runs.

The noise is entirely in the column I built myself.

**One model was deliberately excluded.** `gpt-5.6-sol` cannot use function tools
through the chat-completions endpoint without setting `reasoning_effort` to
`none`. The repair agent *is* a tool loop, so including it would have meant
comparing one model with its reasoning switched off against four with theirs on.
Left out, and the reason recorded here rather than quietly dropped.

## Part 2 — corrections found by checking the work

These matter more than they look: a benchmark that scores the wrong thing
produces confident numbers that mean nothing, and a submission that cannot be
opened is a submission that was not made. Most were found by running the harness
against migrations whose correctness was already known, or by building the
reader's machine instead of trusting that it would work.

### H1 — the 405 probe was hitting a sibling handler

**Tried:** for each route, send one HTTP method the route does not declare and
expect 405.

**Evidence:** on `case_01_inventory`, the 405 probe for `GET /items` sent
`POST /items` — which is a different, existing route. The probe recorded a 400
from the create handler and tested nothing about method rejection.

**Decision:** compute the declared methods per *path* rather than per route, and
emit one 405 probe per path. Covered by
`tests/test_probing.py::test_405_probe_never_hits_a_sibling_handler`.

### H2 — type-blind query probes failed correct migrations

**Tried:** send the string `"probe"` for every query parameter.

**Evidence:** a hand-written, deliberately faithful migration of
`case_01_inventory` scored 93.3% instead of 100%. The single failure was
`?limit=probe`: Flask's `request.args.get("limit", type=int)` returns `None` for
unparseable input and falls back to the configured page size, while a typed
FastAPI parameter rejects it with 422. The probe was generating the difference.

**Decision:** read the `type=` coercion out of the AST and send a value of the
right type on the happy path, then add a dedicated `bad_query_type` probe that
sends garbage on purpose. The real divergence is still measured — it just stopped
contaminating the happy path.

**What it also revealed:** this is a genuine regression class that a reviewer
would miss. A client calling `?limit=abc` gets 200 today and 422 after a naive
migration. It went into the migrator's instructions as an explicit rule.

### H3 — a case with zero routes looked like a clean run

**Tried:** extract routes from `@app.route` and `@app.get`-style decorators.

**Evidence:** `case_08_method_view` registers its views with
`app.add_url_rule(..., view_func=TaskAPI.as_view(...))`. The extractor found no
routes, generated one global probe, and the case reported a passing contract.
Zero coverage is indistinguishable from perfect coverage in a ratio.

**Decision:** resolve `add_url_rule` to its `MethodView` class and derive the
methods from the verb methods defined on it. The case went from 1 probe to 17.
A future version should refuse to score any case whose probe count is
implausibly low rather than relying on a reader to notice.

### H4 — framework error pages were being compared as application behaviour

**Tried:** compare status and body on every probe.

**Evidence:** Flask renders an HTML page for an unrouted 404 and for a 405;
FastAPI returns JSON. Every case lost several probes to a difference no
migration can remove.

**Decision:** when the legacy response is not JSON, compare the status only, and
count those probes in a separate bucket that appears in every report. The
relaxation is visible rather than hidden.

### H5 — probes could not get past a guard or reach a real record

**Tried:** synthesise path parameters from the converter type
(`<int:id>` → `1`, `<name>` → `"probe"`).

**Evidence:** `case_02_blueprint_auth` returned 401 on every probe and
`case_04_error_handlers` returned 404 on every probe. Neither case was testing
anything except its rejection path.

**Decision:** let each case declare fixtures — `probe_headers`, `path_values`,
`body_values` — the way an integration test declares its setup. The harness
never guesses a credential. `case_04` went from `{404: 8, 405: 2}` to a spread
covering 200, 400, 404, 405 and the custom 409.

### H6 — the response cache could never record its first response

**Tried:** cache every model response keyed by the exact request, so the whole
benchmark can be replayed offline and a reader can check the reported numbers.

**Evidence:** after a full baseline run — fourteen completed migrations, real
tokens spent — `data/llm_cache.jsonl` did not exist. Not empty: absent.

The cause is a one-character bug with an unusually nasty shape. `ResponseCache`
defines `__len__`, which makes an *empty* cache falsy in Python. The call site
was `if self.cache: self.cache.put(...)`. An empty cache therefore skipped its
own write, which kept it empty, which kept it falsy. The cache could never
bootstrap, and nothing anywhere reported an error — the runs looked perfect.

**Decision:** compare against `None` explicitly at both call sites, and add
`tests/test_llm_cache.py::test_an_empty_cache_still_records_the_first_response`,
which asserts the trap directly (`assert not cache` alongside
`assert cache is not None`) so the next person to touch it sees why.

**Why it is in this document:** the reproducibility claim was silently false.
Everything else about the run was correct — the numbers, the trajectories, the
report. A judge running `--replay` would have hit `CacheMiss` on the first
prompt and concluded the submission did not work. Nothing surfaced it except
looking at the filesystem for a reason unrelated to the bug.

### H7 — Flask-RESTful resources were invisible

**Tried:** the `add_url_rule` support from H3, applied to the two real
third-party cases.

**Evidence:** `api.add_resource(Todo, "/todos/<string:todo_id>")` is a different
API from `add_url_rule`, so both real cases extracted zero routes. Worse, the
request fields in Flask-RESTful are declared with
`parser.add_argument("task")` at module level, nowhere near the handler that
calls `parse_args()`, so even a resolved route would have been probed with an
empty body.

**Decision:** resolve `add_resource` to its `Resource` class the same way as
`MethodView`, and collect module-level `reqparse` fields onto any handler that
calls `parse_args()`. `case_13_restful_todo` went from 0 to 17 probes covering
200, 201, 204, 400, 404 and 405. Flask-RESTful is one of the most common shapes
in the legacy code this tool exists to migrate; missing it entirely would have
made the benchmark unrepresentative.

### H8 — form handlers were probed with JSON, so they only ever returned 400

**Tried:** send a JSON body to every route that accepts one.

**Evidence:** `case_14_restful_todo_simple` reads `request.form["data"]`. Every
probe sent JSON, every request failed content-type validation, and the recorded
contract was three 400s and nothing else. The case measured the framework's
error handling, not the application.

**Decision:** infer the encoding from what the handler reads. A handler touching
`request.form` gets a form-encoded probe; everything else keeps JSON. Detection
is per-route rather than per-case, so a module mixing both is handled. The case
went from `{400: 2, 405: 1, 500: 3}` to a spread including real 200s.

### H9 — the CLI would have overwritten the user's original Flask file

**Tried:** `run_agent` writes its output to `<out_dir>/<case id>.py`, which is
correct for the benchmark, where the case id and the output directory are
independent.

**Evidence:** found by reading the CLI path rather than by a failing test. In
`migrate.py` the case id is the source file's stem and the output directory is
the source file's directory, so `python src/migrate.py app.py` resolves the
output to `./app.py` — the input. On approval the tool would have written the
migrated FastAPI module over the Flask original it was generated from, and the
legacy code, which is the *specification* this whole approach depends on, would
be gone.

**Decision:** `run_agent` takes an explicit `output_path`, and it refuses
outright when the resolved output is the source file, rather than trying to be
clever about renaming.
`tests/test_orchestrator_e2e.py::test_migration_never_overwrites_its_own_source`
asserts both the refusal and that the original is byte-identical afterwards.

**Why it is in this document:** every test was green, the benchmark was
unaffected, and the only person who would ever have hit it is the actual user
running the tool on their actual repository. Benchmarks do not exercise the
path a real user takes.

### H10 — a parser failure was being scored as a failed migration

**Tried:** read the model's reply as JSON, fall back to a fenced code block,
fall back to "if the text contains `import` and `def`, treat it as code".

**Evidence:** `v1_contract` scored **0% on `case_01_inventory`** — a case the
weaker single-prompt baseline had just completed at 100%. The trajectory showed
why: the model returned a complete, correct FastAPI module inside a JSON object,
then appended two stray characters (`"}`) after the closing brace. `json.loads`
refused it, the fenced-block pattern found nothing, and the last fallback
matched — so the raw JSON blob was handed to the sandbox as Python. It failed to
import, all fifteen probes failed, and the case was recorded as a total
regression.

The number was not wrong by a little. It was measuring the parser.

**Decision:** three changes.

1. Every extraction candidate is validated with `ast.parse` before it is
   accepted, and must contain at least one import *and* one function
   definition. Parsing alone is insufficient — `{"code": "not python"}` is a
   valid Python dict literal, which is precisely how the bad candidate slipped
   through in the first place.
2. A tolerant decoder reads the string that follows `"code":` directly,
   honouring backslash escapes, so trailing garbage or a truncated object no
   longer loses an otherwise complete value.
3. When nothing parses, the migrator retries once with the format constraint
   restated. A formatting failure is not a migration failure and should not be
   scored as one.

`tests/test_extraction.py` covers all eleven shapes, each taken from a reply
that actually occurred.

**Why it is in this document:** this is the failure mode the whole submission
argues about, turned on its author. The harness produced a confident, plausible,
precisely-wrong number, and nothing flagged it. It was caught only because 0%
on a case the *weaker* configuration had aced was too strange to accept — and
noticing that required knowing what the number should roughly have been. An
evaluation you cannot sanity-check is not an evaluation.

### H11 — the reproduction command failed on any machine without a `.env`

**Tried:** ship the response cache so `docker compose run --rm reproduce` works
offline, and read the model name from `MIGRATION_MODEL`.

**Evidence:** found by rsyncing the repository into a clean directory *without*
`.env`, exactly as a judge would clone it, and running the documented command.
Every single case reported `CACHE MISS` and the run aborted on the first prompt:

```
model=openai/gpt-4o-mini  cases=16  REPLAY (offline)  cache_entries=22
  [v0_baseline] case_01_inventory … CACHE MISS
Replay cache does not cover v0_baseline/case_01_inventory.
```

The cache key includes the model. `MIGRATION_MODEL` lives in `.env`, which is
git-ignored — correctly, it holds a credential — so a clean clone fell back to
the compiled-in default, `openai/gpt-4o-mini`, and missed a cache recorded
against `deepseek/deepseek-v4-flash`. The one machine where this could never
reproduce was the only kind of machine that would ever run it.

**Decision:** the cache describes itself. Every record already carried the model
that produced it, so `ResponseCache.recorded_models()` reports them and
`--replay` adopts the recorded model unless `--model` is passed explicitly. A
cache holding several models refuses to guess and says so. Covered by
`test_replay_adopts_the_model_the_cache_was_recorded_with` and
`test_a_mixed_cache_refuses_to_guess`.

### H12 — the host and the container disagreed about the same cached run

**Tried:** verify the clean-clone reproduction against the numbers measured on
the development machine.

**Evidence:** identical cache, identical probes, different answer.
`case_06_query_params` scored 100% on the host and **0%** in the container. The
migrated module imported `uvicorn`; the host happened to have it, the container
did not, the module failed to import, and all six probes failed. To the metric
that is indistinguishable from a migration that broke every route.

**Decision:** pin the packages a generated migration may legitimately reach for
— `uvicorn` and `python-multipart` — so the sandbox matches what a real FastAPI
project has installed, and note in `requirements.txt` *why* they are there. The
alternative, forbidding the imports in the prompt, would have hidden a real
class of migration output rather than supporting it.

**Why it is in this document:** "it reproduces" is a claim about someone else's
machine, and the only way to check it is to build someone else's machine. Two of
the three most serious defects in this project were found in the ten minutes
after deciding to actually do that.

### H13 — the oracle had stopped checking a third of one case

**Tried:** when the legacy response is not JSON, compare only the status code.
The intent was narrow: Flask renders an HTML page for an unrouted 404 and for a
405, FastAPI renders JSON, and no migration can reproduce that markup (H4).

**Evidence:** found while reading a trajectory for an unrelated reason. The
run summary for `case_05_response_shapes` said
`"matched": 13, "matched_status_only": 8`. Eight of thirteen probes were passing
on the status code alone — and that case exists specifically to test a CSV
export, a `text/plain` health endpoint and a 204. Its whole point was the
response bodies, and the bodies were not being compared. A migration returning
an empty CSV with a 200 would have scored 100%.

The rule said "not JSON". It should have said "the framework's own error page".

**Decision:** the exemption now requires a 4xx/5xx status *and* an HTML content
type. `text/csv`, `text/plain`, and an HTML body served with a 200 are all
compared in full. Three tests pin the boundary, including one asserting that an
HTML page returned with a 200 is application output and is compared.

Re-measuring afterwards, `case_05` under `v1_contract` still scores 100% — the
migration really was reproducing those bodies — but on five probes instead of
thirteen's worth of hand-waving, and `matched_status_only` fell from 8 to 5,
which are the genuine framework error pages.

**Why it is in this document:** a relaxation added for a good reason grew past
its justification, and the metric got quieter rather than louder about it. The
only visible symptom was a counter in a JSON blob that nobody had a reason to
read. That counter now appears in every migration report for exactly this
reason.

### H14 — the secret scrubber corrupted the evidence it was protecting

**Tried:** before copying the coding-agent session transcript into the
submission, run a set of credential-shaped regexes over it. Over-redact on
purpose: a false positive costs a reader one token, a false negative publishes a
key.

**Evidence:** the source transcript had **0 unparseable lines out of 1299**. The
scrubbed copy had **3**. Running a regex across raw JSONL can swallow a
backslash that belonged to a JSON escape sequence, and the line stops decoding.
The submission would have shipped a required deliverable that a reader's tools
refuse to open — and the corruption is invisible unless you parse the file,
which nobody does to a log they are merely copying.

**Decision:** scrub the decoded structure, not the text. Each line is parsed,
every string value is redacted recursively, and the record is re-serialised, so
the output is valid by construction. A line that will not decode in the source
is scrubbed as text and reported rather than silently dropped. The script then
re-parses everything it wrote and **exits non-zero rather than shipping a
corrupted transcript**.

Result: 1307 lines, 0 unparseable, 31 redactions.

**Why it is in this document:** the tool whose entire job was protecting the
submission was damaging it, and every check that existed still passed. Writing
the verification step *into* the tool — parse what you just wrote, refuse if it
is broken — is the same move as the rest of this project, applied to itself.

### H17 — a backup of the credentials file was not ignored

**Tried:** keep credentials out of the repository by git-ignoring `.env`, and
verify the built archive rather than the working tree.

**Evidence:** switching provider keys, I made a backup with `cp .env .env.bak`.
`.gitignore` listed `.env` exactly, so `.env.bak` — byte-identical, keys and all
— was tracked. It was caught by a sweep that asked the question directly
(`git check-ignore` on every plausible dotenv name) rather than by looking at
the file I happened to remember creating.

**Decision:** ignore the glob `.env.*` with an explicit `!.env.example`
exception, and harden the archive check to reject any dotenv variant instead of
the one exact filename. The backup was deleted.

**Why it is in this document:** the rule was right and the pattern was too
narrow, which is the same shape as H4 and H13 in this list. A protection that
matches one spelling of the thing it protects against is a protection you will
outgrow the first time you type a slightly different filename — and for a
credentials file, outgrowing it once is enough.

---

## Part 3 — what was removed

Two components, both built, both measured, both cut.

### The analyst brief

+15 LLM calls per run, +60% cost, +53% model time, **+0 shippable migrations**.

It is not that the briefs were wrong. They correctly identified the lenient
`request.get_json(silent=True)` gate, the explicit non-default status codes, the
error-body shapes. The problem is that the repair loop discovers the same facts
*from evidence* and only spends a call when a probe actually fails. Paying a
model to predict problems, ahead of a mechanism that detects them, is paying
twice for the worse answer.

The honest caveat: on a benchmark where the repair loop reaches 100%, no
preceding component can show a gain. The brief might pay for itself on harder
input than anything here — but "might help on cases I do not have" is not
evidence, and shipping it on that basis would be exactly the reasoning this
project argues against.

### The cross-case lesson ledger

Same 40 calls, same $1.1683, same model time as V3, and a ledger containing
**zero lessons** at the end of the run.

This one is a design lesson rather than a bug. Memory was wired to learn only
from failures that survived the repair loop — deliberately, so the ledger could
not fill up with the model's speculation. The repair loop then left no survivors.
A component whose input is another component's failures is dead code the moment
that component stops failing, and no amount of care inside it changes that.

Both remain in the repository, switched off, because the ablation that shows
they do not pay is part of the evidence. `--variants all` reproduces it.

---

## Main failure mode

**The oracle needs to run the legacy application, and most real Flask code
cannot be run in isolation.**

Everything here rests on executing the old app to find out what it does. That
works on a self-contained module. It does not work on
`app/case/case_misp.py` from flowintel — 1017 lines, 39 routes, from which
static analysis happily extracted 171 probes and then could not record a single
response, because the module imports `flask_login` and five sibling packages and
expects a database session and an authenticated user. It is not a program; it is
a fragment of one.

That is not a gap another evening closes. Where the old code cannot run, there
is no oracle, and the argument collapses back to trusting the model. Stubbing
the imports would mean *guessing* what the dependencies do, and a guessed oracle
is precisely the failure this project exists to avoid.

The approach is therefore strongest where migration is easiest, and weakest on
the tangled modules that are the actual reason teams stay on Flask.
[`docs/hard-case.md`](docs/hard-case.md) reports it in full, including the
version worth building next: probe a *running* service over HTTP instead of an
imported module. Same oracle, same metric, no import problem.

**Second failure mode, smaller but visible in the trajectories:** the repair
agent over-inspects. On `case_13` it spent four of eight turns and eighteen
`get_probe_detail` calls before writing anything, and invented a probe id
(`r01.GET.ok`) that does not exist. Exploration is cheap and feels productive,
so a budget spent on it is a budget spent on nothing. It converged here; on a
harder case it would have run out. The fix is to require a `run_differential`
before the budget's midpoint, which is not in this submission because the
behaviour was frozen before the run that produced these numbers.

## Hot take

**LLM-generated tests do not verify an LLM's output — they launder it.**

The test generator and the code generator share the same misreading of the
requirement, so the test encodes the bug as the expectation and reports green.
That is strictly worse than no verification: no verification leaves you
appropriately nervous, and a passing suite makes you merge.

The rule this whole project is built on: **an agent's verifier must draw its
ground truth from something the agent cannot influence.** For a migration that
is easy, and almost nobody does it — the system being replaced is still running,
it is authoritative, and it will answer every question you ask it.

The corollary is uncomfortable and is the thing I would take to the next agent I
build. This benchmark's baseline was right 12 times out of 16. Reliability at
that level does not make verification less necessary; it makes it harder to
justify to yourself, right up until the 3 a.m. page.
