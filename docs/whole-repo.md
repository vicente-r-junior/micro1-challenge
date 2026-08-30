# The whole-repository case: pointing the tool at every module of a real app

`docs/hard-case.md` reports one 1017-line module from one repository. This
document reports what happens when the tool is pointed at *every* route-bearing
module of a real Flask application, one file at a time, with nothing trimmed and
nothing stubbed.

Two repositories were used. The subject is **bepasty-server**; **archivy** was
added afterwards as a cross-check, to find out whether the bepasty result was a
property of that codebase or of the tool. It was the tool.

Nothing from either repository is copied into this one. URLs, commits and
licences only.

## The subjects

| | bepasty-server | archivy |
|---|---|---|
| URL | https://github.com/bepasty/bepasty-server | https://github.com/archivy/archivy |
| Commit | `624f0dd4b6bf3aa000f25e31eb98db56ca48d159` | `bdcdd39ac6cf9f7b3709b984d8be2f0fa898139e` |
| Licence | BSD-2-Clause | MIT |
| Python under the package | 2683 lines, 36 files (tests excluded) | 3586 lines |
| URL rules at runtime | 30 | 35 |
| Role here | primary subject | cross-check |

**Why bepasty.** It is a self-hosted pastebin that has been maintained since
2014, it is not a tutorial, its licence is permissive, it sits in the 500–3000
line range, its README says how to run it, and — the reason it was chosen over
the other candidate — it registers its routes with `add_url_rule` and
`MethodView`, the two styles `src/probing.py` goes out of its way to support.
If the extractor works anywhere outside the decorator case, it should work here.

**Why archivy second.** It is structured the opposite way: `@blueprint.route`
and `@app.route` decorators, a module-level `app`, absolute imports of its own
package. Between them the two repositories cover both common Flask layouts.

### Do they run?

Both, yes.

**bepasty** needed a virtualenv, `pip install -e .`, and a six-line config file
naming a `SECRET_KEY`, a storage directory and `DEFAULT_PERMISSIONS`; the
quickstart documents all of it. Then
`BEPASTY_CONFIG=/tmp/…/bepasty.conf bepasty-server --port 5599` serves. Verified
by hand: `GET /` → 200, `GET /+list` → 200, and a full upload through the REST
API — `POST /apis/rest/items` with a base64 body and a `Content-Range` header →
**201 CREATED**, `Content-Location: /apis/rest/items/zuLDZwK9`, item on disk.

**archivy** needed the same plus `setuptools<81`, because `archivy/models.py`
imports `pkg_resources`. `archivy run` then serves and `GET /` → 302 to the
login page.

That matters for reading the tables below: every failure recorded there is a
failure on an application that works, in an environment where all of its
third-party dependencies are installed. The tool was run from an interpreter
that could import `bepasty`, `archivy`, `flask`, `pygments` and the rest, so no
row below is a missing package.

## How it was run

```bash
python src/migrate.py <module> --model deepseek/deepseek-v4-flash \
       --no-memory --yes --out /tmp/whole-repo-experiment/out/<name>.py
```

One invocation per module, from a working directory outside this repository so
that trajectories, caches and reports land in `/tmp`. `--no-memory` keeps the
lesson ledger out of it, since a ledger built from these runs would confound
them. No module was edited, trimmed, stubbed or reordered.

## bepasty — every module

`add_url_rule` counts the registration calls physically present in that file;
`routes` and `probes` are what `extract_routes`/`synthesize_probes` returned.

| Module | Lines | `add_url_rule` | Routes | Probes | Outcome |
|---|---|---|---|---|---|
| `views/__init__.py` | 38 | 20 | — | — | **crash**: `KeyError: 'form'` at `probing.py:342` |
| `apis/__init__.py` | 18 | 9 | **0** | 1 | relative import |
| `apis/rest.py` | 313 | 0 | 0 | 1 | relative import |
| `apis/lodgeit.py` | 56 | 0 | 0 | 1 | relative import |
| `views/upload.py` | 163 | 0 | 0 | 1 | relative import |
| `views/display.py` | 157 | 0 | 0 | 1 | relative import |
| `views/download.py` | 138 | 0 | 0 | 1 | relative import |
| `views/modify.py` | 59 | 0 | 0 | 1 | relative import |
| `views/setkv.py` | 59 | 0 | 0 | 1 | relative import |
| `views/filelist.py` | 49 | 0 | 0 | 1 | relative import |
| `views/delete.py` | 38 | 0 | 0 | 1 | relative import |
| `views/login.py` | 26 | 0 | 0 | 1 | relative import |
| `views/xstatic.py` | 17 | 0 | 0 | 1 | relative import |
| `views/index.py` | 23 | 0 | 0 | 1 | no Flask instance named `app` |
| `views/qr.py` | 9 | 0 | 0 | 1 | no Flask instance named `app` |
| `app.py` (factory) | 150 | 0 | 0 | 1 | relative import |
| `wsgi.py` (entry point) | 9 | 0 | 0 | 1 | relative import |

"relative import" is `ImportError: attempted relative import with no known
parent package`, raised when the sandbox loads the file as a standalone
`target_app` module.

`app.py` and `wsgi.py` are not route modules; they were tried because they are
what a user reaches for after the leaf modules fail.

**Totals: 17 modules attempted, 0 measurable, 0 model calls, $0.00, every run
finished in 2–4 seconds.** Of bepasty's 30 runtime URL rules the extractor
recovered **0**.

## archivy — every module

| Module | Lines | Routes | Probes | Outcome |
|---|---|---|---|---|
| `archivy/routes.py` | 442 | 20 | 61 | `AssertionError: View function mapping is overwriting an existing endpoint function: index` |
| `archivy/api.py` | 245 | 14 | 56 | no Flask instance named `app` (the module defines a Blueprint) |
| `archivy/__init__.py` | 108 | **0** | **1** | **scored — 100.0% parity, 1/1 probes** |
| `archivy/click_web/__init__.py` | 83 | 0 | 1 | no Flask instance named `app` |

`archivy/__init__.py` timed out at the provider on its first attempt
(`litellm.Timeout` after 180 s). Nothing about the model was measured, so it was
re-run rather than scored, following the denominator rule the README states.
The number above is the re-run.

## The totals

| | Modules attempted | Produced a parity number | Reached full parity |
|---|---|---|---|
| bepasty | 17 | 0 | 0 |
| archivy | 4 | 1 | 1 |
| **Both** | **21** | **1 (4.8%)** | **1** |

**Spend: $0.15 across everything, 14 live model calls.** Twenty of the
twenty-one modules cost nothing at all, because `record_contract` runs before
any agent does and returns early when the legacy app will not run. That part of
the design works exactly as intended.

The single module that produced a number is the subject of the next section, and
the number is wrong.

## The result that matters: a 100% that means nothing

`archivy/archivy/__init__.py` is the module that builds archivy's Flask
application. It imports cleanly, it exposes a module-level `app`, and its last
line is `from archivy import routes`, which attaches every one of the
application's 35 URL rules. So the sandbox ran it, and the harness recorded a
contract.

It recorded **one probe**:

```
GET /__definitely_not_a_route__   →   404, Flask's built-in HTML error page
```

That probe is not derived from the module. It is `global.GET.unknown_path`, the
fixed 404 check `synthesize_probes` appends to every probe set
(`src/probing.py:661`). Zero routes were extracted, so it was the entire set.

The tool then spent 428 seconds, 10 model calls and $0.09 migrating and
repairing against that one probe: 8 repair turns, 3 differential runs. What the
repair agent converged on is in the trajectory — after the second differential
still failed, it added this:

```python
@app.get('/{full_path:path}')
async def catch_all_404(full_path: str):
    return HTMLResponse(content=FLASK_404_BODY, status_code=404)
```

with `FLASK_404_BODY` a hand-copied reproduction of Werkzeug's 404 page. Third
differential: 1/1. The run exited 0 and wrote this into
`<name>_MIGRATION_REPORT.md`:

> **Behaviour preserved.** Every recorded request produces the same status and
> the same response body as the Flask original.
>
> - Behavioural parity: **100.0%** (1/1 probes reproduce the legacy response)

The migrated module serves **none of archivy's 35 routes**. It defines a
FastAPI app whose only behaviour is returning Flask's 404 page for every path.
It is, as measured, a perfect migration.

Two things about this are worth separating.

The verdict is not a rounding error or a near-miss. The measurement was
degenerate — one probe, scored on status only, of a route that does not exist —
and every layer downstream of that treated it as a specification and optimised
against it. The repair loop did exactly what it is built to do. Given a
specification consisting of one 404, the cheapest way to satisfy it is to serve
404 for everything, and it found that.

The report does disclose the shape: it prints `absent_id 1/1` in the probe
breakdown and the sentence "1 probe(s) were compared on status only". The
headline verdict above it is unqualified.

## What broke, specifically

Six things, in the order a reader would hit them.

**1. `KeyError: 'form'` — `src/probing.py:342`.** In
`_routes_from_add_url_rule`, the branch that handles a bare view function builds
a fallback dict when the target is not defined in the same module:

```python
accessed = (
    _extract_accessed_keys(target)
    if target
    else {"body": [], "query": [], "query_types": {}, "header": []}
)
```

`"form"` is missing from it, and the `Route(...)` constructed four lines later
reads `accessed["form"]`. Any `add_url_rule("/x", view_func=name)` where `name`
is imported rather than defined locally crashes the whole run —
`bepasty/views/__init__.py:19` is `blueprint.add_url_rule('/', view_func=index)`.
The traceback comes out of `migrate.py` uncaught, and because it is raised
inside `record_contract` before the first tool call is traced, the trajectory it
leaves behind is a single `run_start` line — **no outcome, no error, no `run_end`.**
An eight-line module reproduces it. The fix is `"form": []`.

**2. `.as_view()` on an imported class is silently dropped.** Same function.
When the view is `X.as_view('n')`, `class_name` is set to `X`, but
`classes.get(class_name)` is `None` because `X` was imported; and since `view`
is an `ast.Call` rather than an `ast.Name`, the second branch does not fire
either. The rule is discarded with no warning and no count.
`bepasty/apis/__init__.py` holds nine such rules and yields zero routes. The
docstring of that very function says the imperative style must not "silently
produce zero probes — which looks like a clean run instead of no run at all".
It does, one level of indirection later. bepasty puts registration in
`views/__init__.py` and `apis/__init__.py` and handlers in sibling files; that
split is ordinary Flask, and it is invisible to a per-file extractor.

**3. Zero routes still produces one probe, and one probe can be 100%.**
`synthesize_probes` always appends `global.GET.unknown_path`, so a route count
of zero yields a probe count of one. `ParityReport.passed` requires
`self.total > 0`, and one satisfies it. Nothing between route extraction and the
final report asks whether the probe set describes the module. This is the defect
that produced the archivy result, and it is the only one here that costs money
and produces a wrong answer rather than an error.

**4. A module that is part of a package gets executed twice.**
`archivy/routes.py` does `from archivy import app` and then decorates that `app`.
The sandbox loads the file as `target_app`, but importing `archivy` has already
run `from archivy import routes` at the bottom of `__init__.py`, so the same
decorators run a second time against the same application object and Flask
raises `AssertionError: View function mapping is overwriting an existing
endpoint function: index`. This is not the documented import problem — the
module imports fine. It is a consequence of loading a package member under a
different module name, and it will hit any module whose own package imports it.

**5. `_find_app` cannot tell a blueprint from an empty file.** It looks for a
module-level Flask instance and otherwise raises "no Flask instance named 'app'
found in module". Four modules here fail that way — `archivy/api.py`,
`archivy/click_web/__init__.py`, `bepasty/views/index.py`, `bepasty/views/qr.py`
— and three of them are blueprints or handlers that would be perfectly probeable
if the harness were given the app to mount them on. The message does not
distinguish "point me at the app instead" from "there is no application here".
`bepasty/app.py` would have failed the same way had it got that far —
`create_app()` is a factory and the runner only looks for instances — but it
never reached the check, because its relative imports fail first.

**6. The repair agent invented a probe id again.** In the archivy run it called
`get_probe_detail(probe_id="probe_01")`, which does not exist, and got
`{"error": "no probe named probe_01"}`. The README already reports this on
`case_13`; it recurs on third-party code.

One thing did not break, and is worth recording. The analyst's brief on the
eight-line reproduction of bepasty's registration pattern opened with: *"Routes
are registered imperatively with `app.add_url_rule(...)` and a class-based view
imported from another module, so static AST scanning does not discover the
route."* The tool diagnosed its own blind spot correctly and then proceeded as
though it had not, because nothing in the pipeline reads that sentence.

### Two reproductions

The two extractor defects were reduced to minimal modules to confirm they are
general rather than bepasty-specific. Both are eight lines, both were written for
this experiment, and neither is third-party code:

- a module registering `add_url_rule('/', view_func=<imported function>)`
  crashes with `KeyError: 'form'` in 2 seconds;
- a module registering `add_url_rule('/thing', view_func=<imported
  class>.as_view('thing'))` extracts 0 routes and synthesises the 1 global
  probe, matching `apis/__init__.py` exactly.

The second run is worth one more note. Both of the migrator's attempts returned
a "migration" that mounts the untouched Flask app inside FastAPI via
`WSGIMiddleware` — the trivial pass-through, which would have scored 100% on the
one probe. The harness rejected both, but for an unrelated reason: the module
contains no `def`, and `_is_migrated_module` requires at least one import *and*
at least one function. The pass-through was blocked by accident, not by a check
for pass-throughs.

## What this changes in the README

The README's stated main failure mode — "the oracle has to run the legacy
application, and most real Flask code cannot be run in isolation" — is confirmed
and, if anything, understated. Package-relative imports alone account for 14 of
the 21 modules; counting the four blueprint modules with no application object
and the one double-registration, 19 of 21 fail because the file is not a
standalone program. All of that held with every dependency installed and both
applications verified working.

The claim that the approach "is strongest where migration is already easiest"
survives this experiment intact.

Two claims need amending.

**`docs/hard-case.md` reports that on flowintel "static extraction handled it
without special-casing" and produced 39 routes and 171 probes, treating route
extraction as the half that works and execution as the half that does not. That
generalises from a codebase that happens to put decorators and handlers in the
same file.** On bepasty the static half found 0 of 30 rules and crashed on the
one file that registers them, and it did so before any question of executability
arose. On archivy it worked as advertised on the two decorator-based modules —
20 routes and 14 — and produced 0 for the app module. The honest revision is
that extraction works when registration and handler live in the same module,
which is a property of the codebase, not of the extractor.

**More importantly, `hard-case.md` frames the boundary as safe: a fragment
cannot answer HTTP, so no number is produced, and the alternative — stubbing —
is rejected because "a guessed oracle is the exact failure this project exists
to avoid".** That is the right principle and this experiment found the hole in
it. No stub was involved. On unmodified third-party code the tool produced a
number, and the number was 100%, and the migration it certified serves none of
the application's routes. The failure mode is not only "the tool cannot measure
most real modules" — it is "when the tool does measure one, nothing checks that
the measurement covers anything". A probe set of one synthetic 404 is
indistinguishable, at every layer below `synthesize_probes`, from a probe set
that describes an application.

The smallest honest fix is a refusal, not a repair: if `extract_routes` returns
nothing, `record_contract` should fail the case the way an unrunnable app fails
it, rather than passing a one-probe contract downstream. That plus `"form": []`
would have turned this experiment's one wrong answer into its twenty-first
error, which is the correct outcome. Neither is implemented here; this document
is a measurement of the tool as it stands, and `src/` was not touched.

## Reproducing this

Both repositories are public and pinned above. Nothing is vendored.

```bash
git clone https://github.com/bepasty/bepasty-server /tmp/bepasty
cd /tmp/bepasty && git checkout 624f0dd4b6bf3aa000f25e31eb98db56ca48d159
python3 -m venv /tmp/venv && /tmp/venv/bin/pip install -e /tmp/bepasty
/tmp/venv/bin/pip install -r /path/to/this/repo/requirements.txt
```

Then run `src/migrate.py` against each file listed in the bepasty table with
`--out` pointing somewhere under `/tmp`. The sixteen import failures are
deterministic and need no API key; only `archivy/__init__.py` calls a model, and
being a live run it will not reproduce byte for byte.
