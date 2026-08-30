"""Getting code out of a model reply.

This is the least glamorous part of the system and the one that quietly ruined a
whole benchmark run: a malformed reply was accepted as source, failed to import,
and the case scored 0% — a number about the parser, not the agent. Every shape
below came from a real reply.
"""

import json

import pytest

from agents import extract_code

MODULE = 'from fastapi import FastAPI\napp = FastAPI()\n\n@app.get("/")\ndef root():\n    return {}\n'
WELL_FORMED = json.dumps({"code": MODULE})


@pytest.mark.parametrize(
    "label, reply",
    [
        ("plain json object", WELL_FORMED),
        ("json with trailing garbage", WELL_FORMED + '"}'),
        ("json inside prose", "Here you go:\n" + WELL_FORMED + "\nHope that helps."),
        ("json in a fence", "```json\n" + WELL_FORMED + "\n```"),
        ("python in a fence", "```python\n" + MODULE + "```"),
        ("bare python", MODULE),
    ],
)
def test_recovers_a_module_from_every_reply_shape(label, reply):
    code = extract_code(reply)
    assert code is not None, label
    assert "FastAPI" in code


@pytest.mark.parametrize(
    "label, reply",
    [
        # A valid Python dict literal, and therefore ast-parseable, which is why
        # parsing alone was not a sufficient test.
        ("json whose value is not python", '{"code": "this is (((not python"}'),
        ("dict that is not a module", '{"a": 1}'),
        ("prose only", "I was unable to migrate this module."),
        ("imports without any handler", "import os\nimport sys"),
        ("empty", ""),
    ],
)
def test_refuses_anything_that_is_not_a_module(label, reply):
    assert extract_code(reply) is None, label


def test_a_truncated_reply_still_yields_the_code_it_did_send():
    """Reasoning models sometimes stop mid-object after the value is complete."""
    truncated = '{"code": ' + json.dumps(MODULE) + ',  "notes": "I ran out of'
    assert extract_code(truncated) is not None
