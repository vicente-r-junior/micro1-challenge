"""The replay path: the benchmark must re-run with no network and no API key.

If this breaks, a judge cannot reproduce the reported numbers, so it is tested
as a first-class feature rather than as a convenience.
"""

import json

import pytest

from llm import CacheMiss, LLMClient, ResponseCache, _key
from tracing import Tracer

SYSTEM, USER = "you migrate code", "migrate this"


def _seed(path, model="openai/gpt-4o-mini", temperature=0.0, content="cached answer"):
    cache = ResponseCache(path)
    key = _key(model, temperature, {"messages": [
        {"role": "system", "content": SYSTEM}, {"role": "user", "content": USER}]})
    cache.put(key, {"model": model, "message": {"content": content, "tool_calls": []},
                    "prompt_tokens": 11, "completion_tokens": 7, "cost_usd": 0.0001,
                    "latency_s": 1.23})
    return cache


def test_replay_answers_from_cache_without_a_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cache = _seed(tmp_path / "cache.jsonl")
    client = LLMClient(cache=cache, replay=True)
    assert client.chat(SYSTEM, USER, tag="migrator") == "cached answer"


def test_replay_fails_loudly_on_a_prompt_it_has_never_seen(tmp_path):
    client = LLMClient(cache=_seed(tmp_path / "c.jsonl"), replay=True)
    with pytest.raises(CacheMiss):
        client.chat(SYSTEM, "a different prompt", tag="migrator")


def test_a_cached_call_still_lands_in_the_trajectory(tmp_path):
    trace = tmp_path / "t.jsonl"
    tracer = Tracer(trace, {})
    LLMClient(cache=_seed(tmp_path / "c.jsonl"), replay=True, tracer=tracer).chat(
        SYSTEM, USER, tag="migrator"
    )
    calls = [json.loads(l) for l in trace.read_text().splitlines() if json.loads(l)["kind"] == "llm_call"]
    assert len(calls) == 1
    assert calls[0]["tag"] == "migrator [cached]"      # replayed, and says so
    assert calls[0]["system"] == SYSTEM                 # prompt kept verbatim
    assert calls[0]["prompt_tokens"] == 11


def test_cache_survives_a_reload_from_disk(tmp_path):
    path = tmp_path / "c.jsonl"
    _seed(path)
    assert len(ResponseCache(path)) == 1


def test_the_cache_key_covers_the_model(tmp_path):
    """A cache recorded on one model must not be replayed as another."""
    client = LLMClient(cache=_seed(tmp_path / "c.jsonl"), replay=True, model="anthropic/claude-sonnet-4-5")
    with pytest.raises(CacheMiss):
        client.chat(SYSTEM, USER, tag="migrator")


def test_an_empty_cache_still_records_the_first_response(tmp_path, monkeypatch):
    """Regression: ResponseCache defines __len__, so an empty one is falsy.

    A truthiness check on the cache made the first write skip itself, which left
    the cache empty, which kept it falsy. Nothing was ever recorded and the whole
    replay story silently did not exist.
    """
    cache = ResponseCache(tmp_path / "fresh.jsonl")
    assert not cache            # empty == falsy: this is the trap
    assert cache is not None

    client = LLMClient(cache=cache, replay=False, model="openai/gpt-4o-mini")

    class FakeMessage:
        content = "hello"
        tool_calls = None

    class FakeResponse:
        choices = [type("C", (), {"message": FakeMessage()})()]
        usage = type("U", (), {"prompt_tokens": 5, "completion_tokens": 3})()

    client._litellm = type("L", (), {"completion": staticmethod(lambda **kw: FakeResponse())})()

    client.chat("sys", "user", tag="t")
    assert len(ResponseCache(tmp_path / "fresh.jsonl")) == 1, "first response was not persisted"


def test_replay_adopts_the_model_the_cache_was_recorded_with(tmp_path):
    """A clean clone has no .env, so the compiled-in default is wrong.

    The cache key includes the model. Falling back to the default on a machine
    that never set MIGRATION_MODEL misses every entry, and the reproduction
    command a judge runs fails on the first prompt. The cache therefore
    describes itself.
    """
    from llm import resolve_model

    cache = _seed(tmp_path / "c.jsonl", model="deepseek/deepseek-v4-flash")
    assert cache.recorded_models() == ["deepseek/deepseek-v4-flash"]

    def fail(message):
        raise AssertionError(f"should not have failed: {message}")

    assert resolve_model(None, cache, replay=True, fail=fail) == "deepseek/deepseek-v4-flash"
    # An explicit choice still wins.
    assert resolve_model("openai/gpt-4o", cache, replay=True, fail=fail) == "openai/gpt-4o"


def test_a_mixed_cache_refuses_to_guess(tmp_path):
    path = tmp_path / "mixed.jsonl"
    _seed(path, model="deepseek/deepseek-v4-flash")
    cache = _seed(path, model="openai/gpt-4o-mini", content="other")
    from llm import resolve_model

    errors = []
    resolve_model(None, cache, replay=True, fail=errors.append)
    assert errors and "several models" in errors[0]


def test_live_default_follows_whichever_provider_key_is_set(monkeypatch):
    """A judge who exports one key and no model should reach that provider.

    The compiled-in fallback used to be OpenAI unconditionally, so someone with
    only a DeepSeek key got an authentication failure against a provider they
    had never configured. The choice now follows the keys actually present.
    """
    import llm

    for env_var, _ in llm.KNOWN_PROVIDERS:
        monkeypatch.delenv(env_var, raising=False)
    monkeypatch.delenv("MIGRATION_MODEL", raising=False)

    # No key at all: the fallback, so the caller raises NoCredentials with its
    # actionable message rather than failing here.
    assert llm.default_model() == llm.FALLBACK_MODEL

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    assert llm.default_model().startswith("deepseek/")

    # An explicit choice always wins over the inferred one.
    monkeypatch.setenv("MIGRATION_MODEL", "anthropic/claude-sonnet-4-5")
    assert llm.default_model() == "anthropic/claude-sonnet-4-5"

    # An empty variable is not a choice — compose passes one through when the
    # operator set nothing.
    monkeypatch.setenv("MIGRATION_MODEL", "")
    assert llm.default_model().startswith("deepseek/")
