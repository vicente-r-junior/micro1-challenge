# The hard case: what happens on real code

Every case in tier A was written for this benchmark. That is honest but it is
also convenient, so this document reports what the tool does when it is pointed
at a real production Flask module that nobody wrote for it.

## The subject

[`app/case/case_misp.py`](https://github.com/flowintel/flowintel/blob/6a6e56af53232fc6a119f7b8a8a24ab5d5d0b729/app/case/case_misp.py)
from **flowintel**, an open-source incident-response platform, pinned at commit
`6a6e56af`. 1017 lines, a Flask blueprint wiring MISP threat-intelligence
objects into case management.

**This module is not in the package you downloaded, and cannot be.** It is
AGPL-3.0: redistributing it would place this repository under that licence, and
the challenge requires every component to be used according to its terms. What
ships is the URL, the pinned commit, the licence, and a fetch script — so the
numbers below are reproducible only with network access, which is the one place
this project asks for any. Everything else runs offline.

The file is AGPL-3.0, so it is not copied into this repository. `case.json`
records the URL, the commit and the licence, and `fetch.py` downloads it on
demand into a git-ignored path. Reproduce with:

```bash
python data/cases/case_99_flowintel_misp/fetch.py
```

## What worked

Static extraction handled it without special-casing:

| | |
|---|---|
| Lines | 1017 |
| Routes discovered | **39** |
| Methods | 18 GET · 21 POST · 1 DELETE |
| Routes with a JSON body | 21 |
| Probes synthesised | **171** |

Nothing in the extractor knew anything about this codebase. It read
`@case_blueprint.route(...)`, resolved the converters, and pulled body keys out
of `request.json[...]` and `data.get(...)` calls.

## What did not work

The contract could not be recorded:

```
ModuleNotFoundError: No module named 'flask_login'
```

and behind that, five intra-package imports:

```python
from .case import case_blueprint, check_user_private_case
from .CaseCore import CaseModel
from . import common_core as CommonModel
from ..connectors import connectors_core as ConnectorModel
from ..db_class.db import ...          # SQLAlchemy models, a live session
```

**The module is not a program. It is a fragment of one.** It has no `app`, it
expects a database session, an authenticated `current_user`, and a blueprint
registered by an application factory somewhere else.

This is not an implementation gap that another evening would close. The oracle
works by *running the old code*, so wherever the old code cannot be run, there
is no oracle — and the whole argument of this project collapses back to "trust
the model". Pretending otherwise by scoring the case on static route coverage
alone would produce a number that looks like the tier-A numbers and means
something entirely different.

## What it revealed

Three things, and they changed the project.

**1. Most real legacy code is tier B.** The approach is strongest exactly where
migration is easiest — small, self-contained services — and weakest on the
tangled modules that are the actual reason teams stay on Flask. Any honest
version of this tool ships with that sentence on the first page.

**2. The obvious fix is worse than it looks.** Stubbing the imports so the module
loads means synthesising a fake `current_user`, a fake session, a fake database.
Every stub is a guess about behaviour, and a guessed oracle is the exact failure
this project exists to avoid. The route to tier A is not stubbing — it is
running the *real* application under `docker compose` and probing it over HTTP,
which is a different and much larger tool.

**3. The body-key heuristic over-collects on real code.** On
`import_event_report` the extractor reported body keys
`["status", "message", "toast_class"]` — those are keys of a *response* dict the
handler builds, not of the request it reads. The consequence is a probe carrying
three extra fields. Both applications receive the same extra fields, so a
faithful migration still matches and the metric stays sound; but a strict
Pydantic model that forbids extra keys would answer 422 where Flask silently
ignored them. That is a real divergence, so the harness is right to surface it —
it just surfaces it for a slightly accidental reason. On the tier-A cases, where
handlers are short, the heuristic did not misfire.

## Where this goes next

The version worth building is the one that probes a running service rather than
an imported module: bring the legacy app up with its real dependencies, record
the contract over HTTP, then stand the migrated app beside it and replay. Same
oracle, same metric, no import problem — and it works on the code that actually
needs migrating.
