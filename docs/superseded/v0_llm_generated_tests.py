"""Agentic legacy-Flask -> FastAPI migration with verification and orchestration.

The migration is intentionally *not* a linear script. It is an agent built on a
bounded validation loop with three nodes plus a mandatory human checkpoint:

    1. RefactorNode      -> rewrites Flask into FastAPI via an LLM.
    2. VerifierNode      -> generates a ``fastapi.testclient.TestClient`` smoke
                            test and runs it inside an isolated subprocess
                            (the sandbox) to catch real runtime errors.
    3. CorrectionLoop    -> on a non-zero exit code it captures the terminal
                            traceback and feeds it back to the RefactorNode.

Only after the sandbox tests pass (or the retry budget is exhausted) is the
human asked, via ``input()``, whether the generated ``fastapi_X.py`` file may be
written to disk. Nothing is saved automatically.

Allowed dependencies: openai, subprocess, pydantic.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from pydantic import BaseModel, Field

try:  # openai is optional at import time; a clear error is raised if used absent.
    from openai import OpenAI
except ImportError:  # pragma: no cover - exercised only when openai is missing.
    OpenAI = None  # type: ignore[assignment]

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

# Hard limit on correction attempts so the loop can never run forever.
MAX_RETRIES = 3

DEFAULT_MODEL = "gpt-4o"
DEFAULT_TIMEOUT_SECONDS = 120

REFACTOR_SYSTEM_PROMPT = (
    "You are a senior backend engineer who migrates legacy Flask applications "
    "to modern FastAPI. You write complete, clean, production-ready code.\n\n"
    "Hard business rules you MUST obey:\n"
    "1. Replace every ``request.get_json()`` call with FastAPI request bodies "
    "   modelled as Pydantic v2 models injected through FastAPI's dependency "
    "   injection (declare the model as a typed request-body parameter).\n"
    "2. Replace every ``current_app`` (including ``current_app.config[...]``) "
    "   with FastAPI dependency injection, for example a ``get_settings`` "
    "   dependency or an explicitly injected configuration object.\n"
    "3. Use Pydantic v2 (``from pydantic import BaseModel, Field``).\n"
    "4. Name the FastAPI application instance ``app``.\n"
    "5. Keep every route path, HTTP method and piece of business logic intact.\n"
    "6. Include all necessary imports so the file runs standalone.\n\n"
    "Return ONLY a valid JSON object with a single key ``code`` whose value is "
    "the complete Python source file as a string. Do not wrap the JSON in "
    "markdown fences and do not add commentary."
)

VERIFIER_SYSTEM_PROMPT = (
    "You are a rigorous test engineer. Given a complete FastAPI application, "
    "write a standalone test script that:\n"
    "1. Imports the app with ``from app import app``.\n"
    "2. Creates ``from fastapi.testclient import TestClient`` and "
    "``client = TestClient(app)``.\n"
    "3. Sends at least one request to EVERY route defined in the app, using "
    "representative request bodies, query parameters and path parameters.\n"
    "4. Where a route accepts a JSON body, also send one invalid payload to "
    "confirm Pydantic v2 rejects it with HTTP 422.\n"
    "5. Uses plain ``assert`` statements. Do NOT use pytest or unittest.\n"
    "6. Finishes by printing ``ALL SANDBOX TESTS PASSED``.\n\n"
    "Return ONLY a valid JSON object with a single key ``test_code`` whose "
    "value is the complete Python script as a string. Do not wrap the JSON in "
    "markdown fences and do not add commentary."
)

FEEDBACK_PROMPT = (
    "The code failed with this runtime error. Fix the implementation and try again."
)

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #


class AgentConfig(BaseModel):
    """Runtime configuration for the migration agent."""

    model: str = Field(default=DEFAULT_MODEL, description="LLM model identifier.")
    api_key: Optional[str] = Field(
        default=None, description="OpenAI-compatible API key (falls back to env)."
    )
    base_url: Optional[str] = Field(
        default=None, description="Optional OpenAI-compatible base URL."
    )
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_retries: int = Field(
        default=MAX_RETRIES,
        ge=0,
        description="Number of correction attempts after the first pass.",
    )
    sandbox_timeout: int = Field(
        default=DEFAULT_TIMEOUT_SECONDS,
        gt=0,
        description="Per-run timeout (seconds) for the sandbox subprocess.",
    )


class MigrationState(BaseModel):
    """Accumulated state flowing through the orchestration loop."""

    source_path: Path
    original_code: str
    fastapi_code: str = ""
    test_code: str = ""
    attempts: int = 0
    passed: bool = False
    last_traceback: str = ""


# --------------------------------------------------------------------------- #
# Small result records
# --------------------------------------------------------------------------- #


@dataclass
class RefactorResult:
    code: str
    raw: str


@dataclass
class VerificationResult:
    passed: bool
    exit_code: Optional[int] = None
    traceback: str = ""
    stdout: str = ""
    stderr: str = ""
    test_code: str = ""


# --------------------------------------------------------------------------- #
# LLM client
# --------------------------------------------------------------------------- #


class LLMClient:
    """Thin, testable wrapper around the OpenAI chat-completions API."""

    def __init__(self, config: AgentConfig) -> None:
        if OpenAI is None:
            raise RuntimeError(
                "The 'openai' package is not installed. Install it with "
                "'pip install openai' before running the migration agent."
            )
        api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "No OpenAI API key found. Set OPENAI_API_KEY or pass --api-key."
            )
        self._client = OpenAI(
            api_key=api_key,
            base_url=config.base_url or os.getenv("OPENAI_BASE_URL") or None,
        )
        self._model = config.model or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL
        self._temperature = config.temperature

    def chat(self, system: str, user: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content
        return (content or "").strip()


# --------------------------------------------------------------------------- #
# Parsing helpers (robust against markdown fences / prose around JSON)
# --------------------------------------------------------------------------- #


def _extract_json(text: str) -> Optional[dict]:
    """Best-effort parse of a JSON object from an LLM reply."""
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_\-]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    try:
        value = json.loads(cleaned)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            value = json.loads(cleaned[start : end + 1])
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            return None
    return None


def _extract_code_block(text: str) -> Optional[str]:
    """Extract a fenced Python code block as a fallback."""
    match = re.search(r"```python\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"```\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


# --------------------------------------------------------------------------- #
# Refactor node
# --------------------------------------------------------------------------- #


class RefactorNode:
    """Rewrites legacy Flask code into FastAPI using the LLM."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def run(
        self,
        original_code: str,
        feedback: Optional[str] = None,
        previous_code: Optional[str] = None,
    ) -> RefactorResult:
        user_parts = [
            "Original legacy Flask code:",
            "```python",
            original_code,
            "```",
        ]

        if feedback is not None:
            user_parts.extend(
                [
                    "",
                    FEEDBACK_PROMPT,
                    "",
                    "Last generated FastAPI code:",
                    "```python",
                    previous_code or "",
                    "```",
                    "",
                    "Runtime traceback from the sandbox:",
                    "```text",
                    feedback,
                    "```",
                ]
            )

        raw = self._llm.chat(REFACTOR_SYSTEM_PROMPT, "\n".join(user_parts))

        data = _extract_json(raw)
        if data and isinstance(data.get("code"), str) and data["code"].strip():
            return RefactorResult(code=data["code"].strip(), raw=raw)

        code = _extract_code_block(raw)
        if code:
            return RefactorResult(code=code, raw=raw)

        raise RuntimeError(
            "RefactorNode returned an unparseable response. The LLM output was:\n"
            f"{raw[:2000]}"
        )


# --------------------------------------------------------------------------- #
# Sandbox (isolated subprocess)
# --------------------------------------------------------------------------- #


class Sandbox:
    """Runs generated code inside a throwaway directory and subprocess."""

    def __init__(self, timeout: int, python: Optional[str] = None) -> None:
        self._timeout = timeout
        self._python = python or sys.executable

    def run(self, app_code: str, test_code: str) -> VerificationResult:
        with tempfile.TemporaryDirectory(prefix="migration_sandbox_") as tmp_dir:
            tmp = Path(tmp_dir)
            (tmp / "app.py").write_text(app_code, encoding="utf-8")
            (tmp / "test_app.py").write_text(test_code, encoding="utf-8")

            try:
                proc = subprocess.run(
                    [self._python, str(tmp / "test_app.py")],
                    capture_output=True,
                    text=True,
                    timeout=self._timeout,
                    cwd=str(tmp),
                )
                return VerificationResult(
                    passed=proc.returncode == 0,
                    exit_code=proc.returncode,
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    test_code=test_code,
                )
            except subprocess.TimeoutExpired as exc:
                return VerificationResult(
                    passed=False,
                    exit_code=None,
                    stdout=exc.stdout or "",
                    stderr=exc.stderr or f"Sandbox timed out after {self._timeout}s.",
                    test_code=test_code,
                )


# --------------------------------------------------------------------------- #
# Verifier node
# --------------------------------------------------------------------------- #

_FORBIDDEN_PATTERNS = (
    (re.compile(r"request\.get_json\s*\("), "request.get_json() is still present"),
    (re.compile(r"\bcurrent_app\b"), "current_app is still present"),
    (re.compile(r"\bFastAPI\s*\("), None),  # presence marker, not a violation
)


class VerifierNode:
    """Generates a TestClient smoke test and validates it in the sandbox.

    Two layers of verification run here:

    * Static checks enforce the migration business rules (``request.get_json``
      and ``current_app`` must be gone, a ``FastAPI`` app must exist).
    * A dynamically generated ``TestClient`` script is executed in an isolated
      subprocess to catch real runtime errors (Pydantic ``ValidationError``,
      import errors, etc.).
    """

    def __init__(self, llm: LLMClient, config: AgentConfig) -> None:
        self._llm = llm
        self._sandbox = Sandbox(timeout=config.sandbox_timeout)

    def run(self, app_code: str) -> VerificationResult:
        static_errors = self._static_checks(app_code)
        if static_errors:
            return VerificationResult(
                passed=False,
                exit_code=None,
                traceback="Static business-rule violation(s):\n" + "\n".join(
                    f"  - {err}" for err in static_errors
                ),
            )

        test_code = self._generate_test(app_code)
        result = self._sandbox.run(app_code, test_code)
        if not result.passed:
            result.traceback = self._format_traceback(result)
        return result

    def _static_checks(self, app_code: str) -> list[str]:
        errors: list[str] = []
        if not re.search(r"\bFastAPI\s*\(", app_code):
            errors.append("No FastAPI application instance was found.")
        if re.search(r"request\.get_json\s*\(", app_code):
            errors.append("request.get_json() is still present.")
        if re.search(r"\bcurrent_app\b", app_code):
            errors.append("current_app is still present.")
        return errors

    def _generate_test(self, app_code: str) -> str:
        user = (
            "FastAPI application to test:\n```python\n" + app_code + "\n```"
        )
        raw = self._llm.chat(VERIFIER_SYSTEM_PROMPT, user)

        data = _extract_json(raw)
        if data and isinstance(data.get("test_code"), str) and data["test_code"].strip():
            return data["test_code"].strip()

        code = _extract_code_block(raw)
        if code:
            return code

        raise RuntimeError(
            "VerifierNode returned an unparseable response. The LLM output was:\n"
            f"{raw[:2000]}"
        )

    @staticmethod
    def _format_traceback(result: VerificationResult) -> str:
        parts: list[str] = []
        if result.exit_code is not None:
            parts.append(f"[exit code {result.exit_code}]")
        if result.stdout.strip():
            parts.append("--- stdout ---\n" + result.stdout.strip())
        if result.stderr.strip():
            parts.append("--- stderr ---\n" + result.stderr.strip())
        return "\n".join(parts) if parts else "Sandbox test failed with no output."


# --------------------------------------------------------------------------- #
# Human checkpoint
# --------------------------------------------------------------------------- #


class HumanCheckpoint:
    """Mandatory approval gate; never writes to disk on its own."""

    CONFIRM_PROMPT = "Migration validated in sandbox. Do you want to apply the changes? (Y/n) "

    def __init__(self, prompt_func: Callable[[str], str] = input) -> None:
        self._prompt = prompt_func

    def approved(self) -> bool:
        answer = self._prompt(self.CONFIRM_PROMPT).strip().lower()
        return answer in ("", "y", "yes")


# --------------------------------------------------------------------------- #
# Orchestrator
# --------------------------------------------------------------------------- #


class MigrationAgent:
    """Coordinates Refactor -> Verify -> Correct with a bounded retry loop."""

    def __init__(self, config: AgentConfig, llm: LLMClient) -> None:
        self._config = config
        self._refactor = RefactorNode(llm)
        self._verifier = VerifierNode(llm, config)
        self._checkpoint = HumanCheckpoint()

    def run(self, source_path: Path) -> MigrationState:
        original_code = source_path.read_text(encoding="utf-8")
        state = MigrationState(source_path=source_path, original_code=original_code)

        feedback: Optional[str] = None
        previous_code: Optional[str] = None

        # attempt 0 is the initial pass; attempts 1..max_retries are corrections.
        for attempt in range(self._config.max_retries + 1):
            state.attempts = attempt + 1
            print(f"\n[agent] Refactor attempt {state.attempts} "
                  f"(budget {self._config.max_retries} retries)")

            try:
                refactor_result = self._refactor.run(
                    original_code, feedback=feedback, previous_code=previous_code
                )
            except RuntimeError as exc:
                print(f"[agent] Refactor node failed: {exc}")
                state.last_traceback = str(exc)
                previous_code = None
                feedback = str(exc)
                continue

            state.fastapi_code = refactor_result.code
            print("[agent] Verifying generated FastAPI code in sandbox...")
            verification = self._verifier.run(refactor_result.code)
            state.test_code = verification.test_code

            if verification.passed:
                state.passed = True
                state.last_traceback = ""
                print("[agent] Sandbox verification PASSED.")
                break

            state.last_traceback = verification.traceback
            print("[agent] Sandbox verification FAILED. Feeding traceback back "
                  "to the refactor node.")
            feedback = verification.traceback
            previous_code = refactor_result.code

        if not state.passed:
            print(
                f"[agent] Retry budget exhausted ({self._config.max_retries} "
                "retries) without a passing sandbox run."
            )

        self._prompt_for_approval(state)
        return state

    def _prompt_for_approval(self, state: MigrationState) -> None:
        if not state.fastapi_code:
            print("[agent] No valid FastAPI code was produced; nothing to save.")
            return

        if not state.passed:
            print("[agent] Warning: the migration did not pass sandbox "
                  "verification. Review before applying.")

        if self._checkpoint.approved():
            output_path = _default_output_path(state.source_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(state.fastapi_code, encoding="utf-8")
            print(f"[agent] Migration applied -> {output_path}")
        else:
            print("[agent] Changes discarded. No file was written.")


def _default_output_path(source_path: Path) -> Path:
    return source_path.with_name(f"fastapi_{source_path.stem}.py")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Agentic Flask -> FastAPI migration with sandboxed "
        "verification and a mandatory human checkpoint."
    )
    parser.add_argument("source", type=Path, help="Path to the legacy Flask file.")
    parser.add_argument("--model", default=None, help="LLM model to use.")
    parser.add_argument("--api-key", default=None, help="API key (or OPENAI_API_KEY).")
    parser.add_argument("--base-url", default=None, help="OpenAI-compatible base URL.")
    parser.add_argument(
        "--max-retries",
        type=int,
        default=MAX_RETRIES,
        help=f"Correction attempts (default {MAX_RETRIES}).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Sandbox subprocess timeout in seconds.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    source = args.source
    if not source.is_file():
        print(f"[agent] error: {source} is not a readable file.", file=sys.stderr)
        return 2

    config = AgentConfig(
        model=args.model or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL,
        api_key=args.api_key or os.getenv("OPENAI_API_KEY"),
        base_url=args.base_url or os.getenv("OPENAI_BASE_URL") or None,
        max_retries=args.max_retries,
        sandbox_timeout=args.timeout,
    )

    try:
        llm = LLMClient(config)
    except RuntimeError as exc:
        print(f"[agent] error: {exc}", file=sys.stderr)
        return 2

    agent = MigrationAgent(config, llm)
    state = agent.run(source)
    return 0 if state.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
