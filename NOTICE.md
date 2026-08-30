# Provenance

## What existed before this competition

Nothing in `src/` did. The migration agent, the differential harness, the probe
generator and the benchmark driver were written for the micro1 Frontier
Engineering Challenge 2026.

Third-party libraries are used under their own licences and are declared in
`requirements.txt`: LiteLLM (MIT), Flask (BSD-3-Clause), FastAPI (MIT), Pydantic
(MIT), httpx (BSD-3-Clause), pytest (MIT).

## Benchmark cases

Every case under `data/cases/` records its origin and licence in its
`case.json`. Cases marked `"origin": "synthetic"` were written for this
benchmark and are covered by this repository's licence. Cases taken from public
repositories record the upstream URL, the pinned commit and the upstream
licence, and keep their original licence headers.

### Third-party code vendored here

| Case | Upstream | Licence |
|---|---|---|
| `case_13_restful_todo` | [flask-restful `examples/todo.py`](https://github.com/flask-restful/flask-restful/blob/88cce53a8cd65830bf1815185a42ba24e5db78c6/examples/todo.py) @ `88cce53` | BSD-3-Clause, Copyright (c) 2013 Twilio, Inc. |
| `case_14_restful_todo_simple` | [flask-restful `examples/todo_simple.py`](https://github.com/flask-restful/flask-restful/blob/88cce53a8cd65830bf1815185a42ba24e5db78c6/examples/todo_simple.py) @ `88cce53` | BSD-3-Clause, Copyright (c) 2013 Twilio, Inc. |

Both are included **unmodified** apart from a prepended comment header stating
their origin and licence. Neither was written for this project.

### Third-party code deliberately NOT vendored

| Case | Upstream | Licence | Why |
|---|---|---|---|
| `case_99_flowintel_misp` | [flowintel `app/case/case_misp.py`](https://github.com/flowintel/flowintel/blob/6a6e56af53232fc6a119f7b8a8a24ab5d5d0b729/app/case/case_misp.py) @ `6a6e56a` | **AGPL-3.0** | Copying it here would place this repository, which micro1 takes ownership of on submission, under the AGPL. Only the URL and pinned commit are committed; `fetch.py` downloads it locally on request, and the download is git-ignored. |

The challenge ground rules state that public or synthetic data are the easiest
options; the synthetic cases exist so the whole benchmark can be replayed
offline, with no dependency on a third party staying online.

## Prior art that shaped the approach

The idea of recording a system's responses and replaying them against a new
implementation is not new — it is the same principle behind
[GitHub Scientist](https://github.com/github/scientist) (branch-by-abstraction
experiments), Twitter's *diffy*, and VCR-style HTTP replay fixtures. What is
specific here is deriving the probe set statically from the legacy routes so no
recorded production traffic is required, and feeding the resulting behavioural
diff back to a repair agent as its feedback signal.

## Coding agents used

Disclosed in `README.md` under "Agent trajectories", with the trajectories
themselves committed under `trajectories/`.
