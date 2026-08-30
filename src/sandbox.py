"""Subprocess execution of untrusted application code, and its limits.

Both the legacy Flask app and the generated FastAPI app are executed here. The
generated app in particular is model output that has never been reviewed, so it
runs in a throwaway directory, in a separate process, under a wall-clock
timeout, and its result comes back as JSON over a file rather than as a live
object. That is enough to keep a crash, a hang or an `exit()` from taking the
harness down with it, and enough that a module which writes to a relative path
writes into a directory that is deleted afterwards.

**It is not a security boundary, and calling it one would be a lie.** This is
`subprocess.run` with a different working directory. There is no namespace, no
seccomp filter, no read-only mount, no unprivileged user and no network block.
Generated code that uses an absolute path can read this repository; code that
opens a socket reaches the network. The isolation that does exist is against
*accidents*, which is what model output mostly produces -- not against a model
that has been prompted to attack the machine.

The reason that is acceptable here is the deployment, not the code: every
command this project documents for a reader runs inside the container defined
by the repository's Dockerfile, and the container is the boundary. Running
`python src/migrate.py` directly on a workstation runs model-written code on
that workstation with the caller's privileges, and `README.md` says so where it
prints that command.

A real boundary would be a per-run container with `--network none`, a read-only
root, a non-root user and CPU and memory limits. That is the correct next step
and it is not implemented.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

RUNNER = Path(__file__).with_name("_runner.py")
DEFAULT_TIMEOUT_S = 90


@dataclass
class SandboxResult:
    ok: bool
    responses: list[dict[str, Any]]
    error: Optional[str]
    stderr: str = ""
    timed_out: bool = False

    @property
    def failure_reason(self) -> Optional[str]:
        if self.ok:
            return None
        if self.timed_out:
            return "sandbox timed out"
        return (self.error or self.stderr or "unknown sandbox failure").strip()


def run_probes(
    app_source: str,
    framework: str,
    probes: list[dict[str, Any]],
    *,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    extra_files: Optional[dict[str, str]] = None,
) -> SandboxResult:
    """Execute ``app_source`` and replay ``probes`` against it.

    ``framework`` is ``"flask"`` or ``"fastapi"``; it selects the test client
    used inside the sandbox. ``extra_files`` are written next to the app, for
    cases whose module imports a local helper.
    """
    with tempfile.TemporaryDirectory(prefix="migration_sandbox_") as tmp:
        root = Path(tmp)
        app_file = root / "target_app.py"
        app_file.write_text(app_source, encoding="utf-8")
        for name, content in (extra_files or {}).items():
            (root / name).write_text(content, encoding="utf-8")

        runner = root / "_runner.py"
        shutil.copyfile(RUNNER, runner)

        job = root / "job.json"
        out = root / "out.json"
        job.write_text(
            json.dumps(
                {"app_file": str(app_file), "framework": framework, "probes": probes}
            ),
            encoding="utf-8",
        )

        try:
            proc = subprocess.run(
                [sys.executable, str(runner), str(job), str(out)],
                capture_output=True,
                text=True,
                timeout=timeout_s,
                cwd=str(root),
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(False, [], f"timed out after {timeout_s}s", timed_out=True)

        if not out.exists():
            return SandboxResult(
                False, [], "sandbox produced no output", stderr=(proc.stderr or "")[-4000:]
            )

        payload = json.loads(out.read_text(encoding="utf-8"))
        return SandboxResult(
            ok=bool(payload.get("ok")),
            responses=payload.get("responses") or [],
            error=payload.get("error"),
            stderr=(proc.stderr or "")[-4000:],
        )
