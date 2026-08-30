"""Environment loading.

Provider credentials are read from a local ``.env`` that is git-ignored, so a
key never enters the repository or the submission archive (ground rule 8). The
loader is deliberately tiny and dependency-free: it only fills variables that
are not already set, so a real environment variable always wins over the file.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_ENV_FILE = Path(".env")


def load_env(path: Path = DEFAULT_ENV_FILE) -> list[str]:
    """Populate os.environ from a KEY=VALUE file. Returns the names it set."""
    if not path.exists():
        return []
    loaded: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded


def describe_providers() -> str:
    """Which provider credentials are present. Never prints a value."""
    known = {
        "OPENAI_API_KEY": "openai",
        "ANTHROPIC_API_KEY": "anthropic",
        "DEEPSEEK_API_KEY": "deepseek",
        "GEMINI_API_KEY": "gemini",
        "GROQ_API_KEY": "groq",
        "OPENROUTER_API_KEY": "openrouter",
    }
    present = [name for var, name in known.items() if os.getenv(var)]
    return ", ".join(present) if present else "none"
