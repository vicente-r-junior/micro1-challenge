# The design that was thrown away

`v0_llm_generated_tests.py` is the first version of this project, written before
the benchmark existed. It is kept here because the reason it was abandoned is
the whole argument of the submission, and because the challenge asks for a clear
account of what changed and why.

## What it did

A three-node loop: an LLM rewrote the Flask app as FastAPI, a second LLM call
wrote a `TestClient` smoke test **for the code the first call had just
produced**, the test ran in a subprocess, and any traceback was fed back for a
retry. A human was asked before anything was written to disk.

Read on its own it looks reasonable. It has a sandbox, a bounded retry budget,
static checks for `request.get_json` and `current_app`, and a human gate.

## Why it was replaced

The verifier is generated from the artefact it is verifying, so it inherits
every decision that artefact made:

```python
# legacy Flask
return jsonify({"error": "item not found"}), 404

# the migration decides to use HTTPException
raise HTTPException(status_code=404, detail="item not found")

# the generated test, written from the migration
assert response.json() == {"detail": "item not found"}   # passes
```

The response body changed shape, every client parsing `error` breaks, and the
suite is green. The test generator and the code generator share one misreading
of the requirement, so the test encodes the bug as the expectation.

Its static checks have the same problem from the other direction: they assert
that `request.get_json` and `current_app` are *absent*, which measures whether
the code looks like FastAPI, not whether it behaves like the Flask app did.
A migration can satisfy both checks and still return different data on every
route.

## What replaced it

The oracle moved out of the model's reach. Routes are read from the legacy
source with `ast`, probes are derived from those routes by fixed rules, and the
probes are replayed against the **original Flask application** to record what it
actually does. That recording is the specification. The migration is then
replayed against the same probes and diffed.

The retry loop survived, but its feedback changed from a Python traceback to a
behavioural diff — "this probe returned 404 `{"error": ...}` before and returns
404 `{"detail": ...}` now" — which is a statement about the requirement rather
than about the crash.

The human gate survived unchanged. It was the one part that was already right.
