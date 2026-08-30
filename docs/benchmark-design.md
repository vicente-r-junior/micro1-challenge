# How the benchmark was built, and why to distrust half of it

A benchmark written by the author of the tool it evaluates is evidence about the
author's imagination, not about the tool. This document says exactly how each
case was chosen so a reader can discount it appropriately.

## The cases

| | Count | Origin |
|---|---|---|
| Tier A, synthetic | 14 | Written for this benchmark |
| Tier A, third-party | 2 | flask-restful `examples/`, BSD-3-Clause, vendored unmodified |
| Tier B, third-party | 1 | flowintel, AGPL-3.0, fetched on demand, **not scorable** |

212 probes across the 16 scorable cases.

### The synthetic ones

Each targets a specific way a Flask→FastAPI migration loses behaviour, chosen by
listing the mistakes I expected a model to make: blueprint `before_request`
guards, `current_app.config`, `@errorhandler`, non-JSON responses, typed query
parameters with lenient coercion, path converters, `MethodView`, a JSON array
body with a 207, `If-Match` preconditions, trailing-slash redirects, pagination
headers. Two later ones are deliberately harder — a gateway carrying three
generations of error handling at once, and an order state machine with
idempotency keys.

They are all self-contained, deterministic and offline, which is what makes
`make reproduce` possible.

### The real ones

`examples/todo.py` and `examples/todo_simple.py` from **flask-restful**, pinned
at commit `88cce53` and included byte-for-byte apart from a licence header. They
were chosen for a boring reason: they are among the very few real Flask modules
that can be imported without a database, a config object and an application
factory. That constraint is itself a finding — see
[`hard-case.md`](hard-case.md).

## What the split showed

The baseline — one direct prompt, no verification — produced:

| | Shippable (every probe matches) |
|---|---|
| Synthetic cases | **12 / 14** |
| Third-party cases | **0 / 2** |

Same model, same prompt, same harness, same run.

I designed fourteen traps and a modern model walked through twelve of them. Then
it hit a hundred and twenty-two lines of open-source code it had never been aimed at
and failed both, by:

- **dropping a route entirely** — `GET /todos` returned 200 before the migration
  and 405 after it
- **rewriting every error envelope** — Flask-RESTful answers
  `{"message": "The method is not allowed for the requested URL."}`; the
  migration answers `{"detail": "Method Not Allowed"}`
- **tightening validation that was deliberately loose** — `reqparse` coerces
  `12345` into `"12345"` and returns 201; the Pydantic model rejects it with 422
- **fixing a bug** — an unhandled `KeyError` that used to surface as a 500 became
  a tidy 404

That last one is the most interesting failure in the whole benchmark, because
the migration is *better* than the original. It is also a change every client
with a `try/except HTTPError` around a 500 will notice. A migration is not
allowed to improve behaviour any more than it is allowed to degrade it, and no
reviewer reading that diff would have flagged it.

## Why the synthetic cases were too easy

Writing a case means naming the trap, and naming the trap means the trap is one
I already knew about. The cases are therefore a catalogue of *anticipated*
failure modes, and a model trained on the same public discussions of
Flask-to-FastAPI migration has seen the same catalogue. Real code fails
differently: not on the famous traps, but on the accumulated small decisions
nobody wrote a blog post about.

The honest conclusion is that **the third-party column is the one worth reading**,
and that two cases is a small sample. The strongest thing this benchmark could
gain is more real code — which is exactly what tier B shows is hard to get, since
most real Flask modules cannot be executed in isolation.

## What would make it better

1. More third-party cases, weighted over synthetic ones.
2. Probing a *running* service over HTTP instead of an imported module, which
   removes the self-containment requirement and unlocks tier B entirely.
3. Cases sampled by someone other than the tool's author.
