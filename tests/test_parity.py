"""The oracle must catch silent regressions and must not invent them."""

from parity import compare, normalise

PROBES = [
    {"id": "p1", "kind": "happy", "route": "/x"},
    {"id": "p2", "kind": "absent_id", "route": "/x/{}"},
]


def _resp(pid, status, body, content_type="application/json"):
    return {"probe_id": pid, "status": status, "json": body, "text": None,
            "content_type": content_type, "error": None}


def test_identical_behaviour_is_full_parity():
    legacy = [_resp("p1", 200, {"a": 1}), _resp("p2", 404, {"error": "nope"})]
    report = compare(PROBES, legacy, list(legacy))
    assert report.parity_strict == 1.0
    assert report.passed


def test_detects_the_error_to_detail_rewrite():
    """HTTPException turns {"error": ...} into {"detail": ...}; clients break."""
    legacy = [_resp("p1", 200, {"a": 1}), _resp("p2", 404, {"error": "nope"})]
    migrated = [_resp("p1", 200, {"a": 1}), _resp("p2", 404, {"detail": "nope"})]
    report = compare(PROBES, legacy, migrated)
    assert not report.passed
    assert report.failures[0].verdict == "body_differs"


def test_400_to_422_is_reported_separately_not_hidden():
    legacy = [_resp("p1", 400, {"error": "bad"}), _resp("p2", 404, {"error": "nope"})]
    migrated = [_resp("p1", 422, {"detail": []}), _resp("p2", 404, {"error": "nope"})]
    report = compare(PROBES, legacy, migrated)
    assert report.parity_strict == 0.5      # the headline number does not forgive it
    assert report.parity_lenient == 1.0     # but it is visible as a known class
    assert report.accepted == 1


def test_framework_error_pages_compare_on_status_only():
    """Flask renders HTML for 404, FastAPI renders JSON. Not app behaviour."""
    legacy = [_resp("p1", 200, {"a": 1}),
              {"probe_id": "p2", "status": 404, "json": None,
               "text": "<!doctype html>...", "content_type": "text/html", "error": None}]
    migrated = [_resp("p1", 200, {"a": 1}), _resp("p2", 404, {"detail": "Not Found"})]
    report = compare(PROBES, legacy, migrated)
    assert report.passed
    assert report.status_only == 1


def test_missing_response_is_a_failure_not_a_pass():
    legacy = [_resp("p1", 200, {"a": 1}), _resp("p2", 404, {"error": "nope"})]
    report = compare(PROBES, legacy, [legacy[0]])
    assert report.failures[0].verdict == "missing"


def test_normalise_erases_only_volatile_values():
    before = {"id": "3f2504e0-4f89-41d3-9a0c-0305e82c3301", "at": "2024-01-01T10:00:00Z", "n": 1}
    after = {"id": "9a0c0305-e82c-4330-8f89-41d33f2504e0", "at": "2025-06-02T22:31:11Z", "n": 1}
    assert normalise(before) == normalise(after)
    assert normalise({"n": 1}) != normalise({"n": 2})


def test_a_csv_body_is_compared_in_full():
    """text/csv is application output, not a framework error page.

    Relaxing the body check for every non-JSON response meant a migration could
    return an empty export and still score 100%.
    """
    csv_ok = {"probe_id": "p1", "status": 200, "json": None, "text": "id,name\n1,bolt\n",
              "content_type": "text/csv; charset=utf-8", "error": None}
    csv_empty = {**csv_ok, "text": ""}
    report = compare(PROBES[:1], [csv_ok], [csv_empty])
    assert not report.passed
    assert report.failures[0].verdict == "body_differs"


def test_a_plain_text_body_is_compared_in_full():
    ok = {"probe_id": "p1", "status": 200, "json": None, "text": "pong",
          "content_type": "text/plain; charset=utf-8", "error": None}
    changed = {**ok, "text": "PONG"}
    assert not compare(PROBES[:1], [ok], [changed]).passed
    assert compare(PROBES[:1], [ok], [dict(ok)]).passed


def test_only_the_framework_error_page_is_exempt():
    """A 404 rendered as HTML by Flask cannot be reproduced by FastAPI."""
    flask_404 = {"probe_id": "p1", "status": 404, "json": None,
                 "text": "<!doctype html><title>Not Found</title>",
                 "content_type": "text/html; charset=utf-8", "error": None}
    fastapi_404 = {"probe_id": "p1", "status": 404, "json": {"detail": "Not Found"},
                   "text": None, "content_type": "application/json", "error": None}
    report = compare(PROBES[:1], [flask_404], [fastapi_404])
    assert report.passed and report.status_only == 1

    # But an HTML body on a 200 is a page the application meant to serve.
    page = {**flask_404, "status": 200, "text": "<h1>dashboard</h1>"}
    other = {**page, "text": "<h1>different</h1>"}
    assert not compare(PROBES[:1], [page], [other]).passed
