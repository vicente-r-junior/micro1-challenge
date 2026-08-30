# One repair, start to finish

A walkthrough of a single real run, `v2_repair` on `case_14_restful_todo_simple`,
taken verbatim from
[`trajectories/v2_repair/case_14_restful_todo_simple.jsonl`](../trajectories/v2_repair/case_14_restful_todo_simple.jsonl).
Read it with:

```bash
python src/show_trajectory.py trajectories/v2_repair/case_14_restful_todo_simple.jsonl
```

The case is 50 lines of real third-party code — `examples/todo_simple.py` from
flask-restful, vendored unmodified. Nothing about it was written with this tool
in mind.

## Where it started

| | Behavioural parity |
|---|---|
| `v0_baseline` — one direct prompt | 33% (3/9 probes) |
| `v1_contract` — behaviour-preservation prompt, no repair | 67% (6/9) |
| `v2_repair` — the tool loop | **100% (9/9)** |

Five model calls, 132 seconds, $0.065.

## What the agent actually did

**Turn 1 — read the failures it was given.** The differential handed it a diff,
not a traceback. It pulled three probes in one turn:

```
→ get_probe_detail(r00.POST.wrong_method)
←   legacy: 405 {"message": "The method is not allowed for the requested URL."}
    candidate: 405 {"detail": "Method Not Allowed"}
→ get_probe_detail(r01.PUT.malformed_json)
←   legacy: 400 {"message": "The browser (or proxy) sent a request that this server could not understand."}
→ get_probe_detail(r01.PUT.missing_field)
```

**Turn 2 — formed a hypothesis and went looking for it in the source.**

```
→ search_legacy("KeyError")                                    ← no matches
→ search_legacy("browser")                                     ← no matches
→ search_legacy("Method Not Allowed|error_router|def handle_error")  ← no matches
```

All three came back empty. This is the interesting moment: those error strings
are in the responses but nowhere in the application. A fixed pipeline has no
move here. The agent had to conclude something.

**Turn 3 — changed strategy, correctly.**

```
→ search_legacy("add_resource|Resource|request\.form")
←   12: from flask_restful import Resource, Api
    19: class TodoSimple(Resource):
    45:     todos[todo_id] = request.form['data']
    48: api.add_resource(TodoSimple, '/<string:todo_id>')
→ search_legacy("app\.|Api|api =")
←   15: api = Api(app)
```

It worked out that the error envelope belongs to **`Api(app)`**, the
Flask-RESTful wrapper — not to the application code at all. That is why grepping
the module for the message text found nothing.

**Turn 4 — wrote a candidate and tested it before committing.**

```
→ run_differential(<complete module>)
← {"run": 1, "budget_left": 2, "parity_strict": 1.0, "matched": 9, "probes": 9}
```

Full parity on the first candidate. The loop stopped there rather than spending
the remaining turns.

## What it wrote

A `StarletteHTTPException` handler reproducing Flask-RESTful's envelope exactly:

```python
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 405:
        return JSONResponse(
            {"message": "The method is not allowed for the requested URL."},
            status_code=405,
        )
    ...
```

And the line that matters most:

```python
        return JSONResponse({"message": "Internal Server Error"}, status_code=500)
```

The legacy app raises an unhandled `KeyError` on a missing todo, which surfaces
as a 500. The baseline migration "fixed" it into a tidy 404. **The repair agent
put the 500 back.**

It did not do that because it was told to preserve 500s. It did it because the
oracle — the running Flask app — answered 500, and the oracle is the
specification. An agent whose verifier was a model would have been congratulated
for the 404.

## Why this counts as agentic

Nothing in the orchestrator decided any of the above. The loop only bounds how
long the agent may keep going: eight turns, three differential runs. Within
that, the agent chose which probes to open, chose to grep the source, chose what
to grep for, drew a conclusion from three empty results, and chose when to stop.

It also wasted calls — it invented a probe id, `r01.GET.ok`, that does not
exist, and got an error back. That is in the trajectory too. The budget exists
because this happens.
