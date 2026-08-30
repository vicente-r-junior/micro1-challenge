"""Model access: one interface, any provider, every call traced and cacheable.

Transport is LiteLLM, so the model is a string like ``openai/gpt-4o-mini``,
``anthropic/claude-sonnet-4-5`` or ``deepseek/deepseek-chat`` and nothing in the
agent code changes when it moves. That matters for the claim this project makes:
the failure being fixed is the *absence of an oracle*, not a weak model, and the
only way to show that is to run the same harness across providers.

Two behaviours are layered on top of the transport:

**Tracing.** No code path can reach a model without going through this class, so
every prompt, completion, token count and cost lands in the run's trajectory.

**Replay cache.** Responses are keyed by a hash of the exact request and stored
in a JSONL file that ships with the repository. With ``--replay`` the whole
benchmark re-runs from that cache: no network, no API key, no spend, and the
numbers in the report come out identical. Without it, a reader could not
reproduce the results at all -- these models are not deterministic even at
temperature 0.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Optional

from tracing import Tracer

# Ordered by how well each performed in the reported benchmark, so a live run on
# a machine that set one key and no model still picks a sensible model rather
# than failing against a provider the operator never configured.
KNOWN_PROVIDERS = (
    ("DEEPSEEK_API_KEY", "deepseek/deepseek-v4-flash"),
    ("ANTHROPIC_API_KEY", "anthropic/claude-sonnet-4-5"),
    ("OPENAI_API_KEY", "openai/gpt-4o-mini"),
)
FALLBACK_MODEL = "openai/gpt-4o-mini"


def default_model() -> str:
    """The model a live run uses when nobody named one.

    ``MIGRATION_MODEL`` wins if it is set. Otherwise the choice follows the keys
    that are actually present: a judge who exports one provider key and runs the
    demo should reach that provider, not whichever one happened to be compiled
    in. With no key at all the fallback is returned so the caller raises
    ``NoCredentials`` with its actionable message instead of a KeyError here.
    """
    named = os.getenv("MIGRATION_MODEL")
    if named:
        return named
    for env_var, model in KNOWN_PROVIDERS:
        if os.getenv(env_var, "").strip():
            return model
    return FALLBACK_MODEL


DEFAULT_MODEL = default_model()


class LLMError(RuntimeError):
    pass


class CacheMiss(LLMError):
    """Raised in replay mode when a request is not in the cache."""


class NoCredentials(LLMError):
    """The provider rejected the request for lack of a usable key.

    Raised in place of the provider SDK's own exception so the person running
    the tool gets a sentence they can act on instead of a stack trace from three
    libraries down.
    """


def _key(model: str, temperature: float, payload: Any) -> str:
    blob = json.dumps(
        {"model": model, "temperature": temperature, "payload": payload},
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class ResponseCache:
    """JSONL-backed request -> response cache, committed with the repository."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        # Cases are evaluated concurrently, so reads and the append-on-write
        # both have to be serialised or the JSONL ends up interleaved.
        self._lock = threading.Lock()
        self._data: dict[str, dict[str, Any]] = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self._data[record["key"]] = record

    def get(self, key: str) -> Optional[dict[str, Any]]:
        with self._lock:
            return self._data.get(key)

    def put(self, key: str, record: dict[str, Any]) -> None:
        with self._lock:
            if key in self._data:
                return
            self._data[key] = record
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"key": key, **record}, ensure_ascii=False, default=str) + "\n")

    def __len__(self) -> int:
        return len(self._data)

    def recorded_models(self) -> list[str]:
        """Which models this cache was recorded against.

        The cache key includes the model, so replaying under a different one
        misses every entry. Rather than make the reader guess, the cache
        describes itself: every record carries the model that produced it, and
        replay defaults to it. Without this a clean clone falls back to the
        compiled-in default, misses the entire cache, and the reproduction
        command fails on a machine that has no .env.
        """
        with self._lock:
            return sorted({r["model"] for r in self._data.values() if r.get("model")})


def _usage(response: Any) -> tuple[int, int]:
    usage = getattr(response, "usage", None)
    return (
        int(getattr(usage, "prompt_tokens", 0) or 0),
        int(getattr(usage, "completion_tokens", 0) or 0),
    )


def _cannot_call(exc: Exception) -> Optional[str]:
    """Is the provider refusing to serve us at all, and why?

    A missing key, a rejected key and an empty balance are three different
    errors from the SDK and the same problem for the person at the keyboard:
    this model will not answer. Each gets a sentence they can act on instead of
    a stack trace from three libraries down.
    """
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    if "no credits" in text or "insufficient" in text or "quota" in text or "billing" in text:
        return "the account has no credits left"
    if (
        "authentication" in name
        or "permissiondenied" in name
        or "api_key" in text
        or "api key" in text
        or "unauthorized" in text
    ):
        return "no usable API key"
    return None


def _rejects_temperature(exc: Exception) -> bool:
    """Does this error mean the model refuses an explicit temperature?"""
    text = str(exc).lower()
    return "temperature" in text and (
        "does not support" in text or "unsupported value" in text or "only the default" in text
    )


def _cost(response: Any) -> Optional[float]:
    try:
        import litellm

        value = litellm.completion_cost(completion_response=response)
        return float(value) if value is not None else None
    except Exception:
        # Unknown or self-hosted model: report nothing rather than invent a price.
        return None


class LLMClient:
    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.0,
        tracer: Optional[Tracer] = None,
        cache: Optional[ResponseCache] = None,
        replay: bool = False,
        api_base: Optional[str] = None,
        timeout: int = 180,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.tracer = tracer
        self.cache = cache
        self.replay = replay
        self.api_base = api_base or os.getenv("MIGRATION_API_BASE") or None
        self.timeout = timeout
        # Some models reject an explicit temperature and accept only their own
        # default. Discovered on the first call and remembered per model, so the
        # rest of the run does not pay for the same rejection repeatedly.
        self._omit_temperature = False
        self._litellm = None
        if not replay:
            try:
                import litellm
            except ImportError as exc:  # pragma: no cover
                raise LLMError("pip install litellm") from exc
            litellm.drop_params = True  # a provider that lacks a param ignores it
            litellm.suppress_debug_info = True
            # A reasoning model under concurrency can leave a socket open long
            # past the per-request timeout, which stalls the whole benchmark
            # with no error to look at. Setting it globally as well as per call
            # makes the ceiling actually bite.
            litellm.request_timeout = timeout
            self._litellm = litellm

    # -- plain completion ---------------------------------------------------- #

    def chat(self, system: str, user: str, *, tag: str, attempt: int = 0) -> str:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        record = self._complete({"messages": messages}, messages, None, tag=tag, attempt=attempt)
        return record["message"]["content"] or ""

    # -- tool-calling turn --------------------------------------------------- #

    def converse(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        *,
        tag: str,
        attempt: int = 0,
    ) -> dict[str, Any]:
        """One turn of a tool-calling loop.

        Returns ``{"content": str|None, "tool_calls": [{"id","name","arguments"}]}``.
        Keyed on the full message list, so a replay walks the identical sequence.
        """
        record = self._complete(
            {"messages": messages, "tools": tools}, messages, tools, tag=tag, attempt=attempt
        )
        return record["message"]

    # -- shared path --------------------------------------------------------- #

    def _complete(
        self,
        cache_payload: dict[str, Any],
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]],
        *,
        tag: str,
        attempt: int,
    ) -> dict[str, Any]:
        key = _key(self.model, self.temperature, cache_payload)

        # `if self.cache` would be False while the cache is empty, because
        # ResponseCache defines __len__. An empty cache would then skip its own
        # write and stay empty forever. Compare against None explicitly.
        cached = self.cache.get(key) if self.cache is not None else None
        if cached is not None:
            self._trace(tag, attempt, messages, cached, cached=True)
            return cached

        if self.replay:
            raise CacheMiss(
                f"Request not in the replay cache (tag={tag}, key={key[:12]}, model={self.model}). "
                "The cache was recorded for one model and case set; rebuild it with "
                "a provider key and without --replay."
            )

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "timeout": self.timeout,
        }
        if not self._omit_temperature:
            kwargs["temperature"] = self.temperature
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if self.api_base:
            kwargs["api_base"] = self.api_base

        started = time.time()
        try:
            response = self._litellm.completion(**kwargs)  # type: ignore[union-attr]
        except Exception as exc:
            reason = _cannot_call(exc)
            if reason:
                raise NoCredentials(
                    f"{self.model} will not answer: {reason}.\n\n"
                    "  Either fix the account or use a different provider --\n"
                    "      edit .env: MIGRATION_MODEL and the matching key\n\n"
                    "  or use the committed cache instead, which needs no key:\n"
                    "      --replay\n\n"
                    "  Note that --replay only covers the benchmark's own cases. Migrating\n"
                    "  a new file is a new prompt, so that needs a live model."
                ) from None
            if not _rejects_temperature(exc) or self._omit_temperature:
                raise
            # Retry on the model's own default rather than failing the case. The
            # cache key still records the temperature that was *requested*, so
            # keys stay stable; `temperature_omitted` records what was sent.
            self._omit_temperature = True
            kwargs.pop("temperature", None)
            response = self._litellm.completion(**kwargs)  # type: ignore[union-attr]
        latency = time.time() - started

        choice = response.choices[0].message
        message = {
            "content": getattr(choice, "content", None),
            "tool_calls": [
                {"id": tc.id, "name": tc.function.name, "arguments": tc.function.arguments}
                for tc in (getattr(choice, "tool_calls", None) or [])
            ],
        }
        prompt_tokens, completion_tokens = _usage(response)
        record = {
            "model": self.model,
            "message": message,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": _cost(response),
            "latency_s": latency,
            "temperature_omitted": self._omit_temperature,
        }
        if self.cache is not None:
            self.cache.put(key, record)
        self._trace(tag, attempt, messages, record, cached=False)
        return record

    def _trace(
        self,
        tag: str,
        attempt: int,
        messages: list[dict[str, Any]],
        record: dict[str, Any],
        *,
        cached: bool,
    ) -> None:
        if self.tracer is None:
            return
        system = next((m.get("content") for m in messages if m.get("role") == "system"), "")
        last = next(
            (m for m in reversed(messages) if m.get("role") != "system"),
            {},
        )
        message = record["message"]
        completion = message.get("content") or ""
        if message.get("tool_calls"):
            completion = (completion + "\n" if completion else "") + json.dumps(
                {"tool_calls": message["tool_calls"]}, ensure_ascii=False
            )
        self.tracer.llm_call(
            tag=f"{tag}{' [cached]' if cached else ''}",
            model=record.get("model", self.model),
            system=str(system or ""),
            user=json.dumps(last, ensure_ascii=False, default=str),
            completion=completion,
            prompt_tokens=record.get("prompt_tokens", 0),
            completion_tokens=record.get("completion_tokens", 0),
            # The latency recorded when the call was actually made, even on a
            # replay. Reporting 0 for cached calls would make a replayed run
            # look free in a way a live run never is; the tag already says the
            # response came from the cache.
            latency_s=record.get("latency_s", 0.0),
            attempt=attempt,
            cost_usd=record.get("cost_usd"),
        )


def resolve_model(requested, cache, replay: bool, fail) -> str:
    """Decide which model string to use.

    An explicit ``--model`` always wins. Otherwise a replay adopts the model the
    cache was recorded with, so the reproduction command works on a machine that
    has never seen a .env file. Only a live run falls back to the compiled-in
    default, which follows whichever provider key is actually set.
    """
    if requested:
        return requested
    if replay and cache is not None:
        recorded = cache.recorded_models()
        if len(recorded) == 1:
            return recorded[0]
        if len(recorded) > 1:
            fail(
                "this cache holds responses from several models "
                f"({', '.join(recorded)}); pass --model to choose one"
            )
        fail("the replay cache is empty; record it first with a provider key")
    return default_model()
