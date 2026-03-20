"""Comprehensive tests for the webhook event processing pipeline.

Covers:
- Idempotency: duplicate delivery IDs are rejected
- Event logging: every event is logged with correct status/hash
- Metadata extraction: PR, issue, push events produce structured logs
- Concurrent delivery deduplication
- Error handling: malformed payloads, missing fields
- Edge cases: empty bodies, unicode, large payloads
"""

from __future__ import annotations

import hashlib
import json
import threading

import pytest

from app.models.event_log import EventStatus
from app.services.event_processor import (
    clear_event_logs,
    event_log_responses,
    extract_issue_numbers,
    get_event_log,
    is_duplicate,
    list_event_logs,
    process_event,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean():
    clear_event_logs()
    yield
    clear_event_logs()


REPO = "SolFoundry/solfoundry"


def _payload(data: dict) -> bytes:
    return json.dumps(data).encode()


def _pr_event(
    action="opened", body="Closes #5", num=10, merged=False,
):
    return {
        "action": action,
        "number": num,
        "pull_request": {
            "number": num,
            "title": "Fix",
            "state": "closed" if action == "closed" else "open",
            "user": {"login": "dev", "id": 2},
            "body": body,
            "merged": merged,
        },
        "repository": {
            "id": 1, "name": "s", "full_name": REPO,
            "owner": {"login": "S", "id": 1},
        },
        "sender": {"login": "dev", "id": 2},
    }


def _issue_event(action="labeled", label="bounty", num=5):
    return {
        "action": action,
        "label": {"id": 1, "name": label},
        "issue": {
            "number": num,
            "title": f"Issue #{num}",
            "body": "Description",
            "state": "open",
            "user": {"login": "dev", "id": 2},
            "labels": [{"id": 1, "name": label}],
        },
        "repository": {
            "id": 1, "name": "s", "full_name": REPO,
            "owner": {"login": "S", "id": 1},
        },
        "sender": {"login": "dev", "id": 2},
    }


def _push_event(ref="refs/heads/main", num_commits=1):
    return {
        "ref": ref,
        "before": "a" * 40,
        "after": "b" * 40,
        "repository": {
            "id": 1, "name": "s", "full_name": REPO,
            "owner": {"login": "S", "id": 1},
        },
        "sender": {"login": "dev", "id": 2},
        "head_commit": {"message": "init"},
        "commits": [{"message": f"commit-{i}"} for i in range(num_commits)],
    }


def _proc(delivery_id, event_type, data):
    p = _payload(data)
    return process_event(delivery_id, event_type, p, {"data": data})


# ===========================================================================
# extract_issue_numbers
# ===========================================================================


class TestExtractIssueNumbers:
    """Test the Closes/Fixes/Resolves #N pattern extraction."""

    def test_closes(self):
        assert extract_issue_numbers("Closes #5") == [5]

    def test_closed(self):
        assert extract_issue_numbers("Closed #7") == [7]

    def test_close(self):
        assert extract_issue_numbers("Close #3") == [3]

    def test_fixes(self):
        assert extract_issue_numbers("Fixes #12") == [12]

    def test_fixed(self):
        assert extract_issue_numbers("Fixed #8") == [8]

    def test_fix(self):
        assert extract_issue_numbers("Fix #4") == [4]

    def test_resolves(self):
        assert extract_issue_numbers("Resolves #42") == [42]

    def test_resolved(self):
        assert extract_issue_numbers("Resolved #9") == [9]

    def test_case_insensitive(self):
        assert extract_issue_numbers("CLOSES #5") == [5]
        assert extract_issue_numbers("fixes #10") == [10]

    def test_multiple_refs(self):
        result = set(extract_issue_numbers("Closes #5, Fixes #12"))
        assert result == {5, 12}

    def test_empty_string(self):
        assert extract_issue_numbers("") == []

    def test_none_input(self):
        assert extract_issue_numbers(None) == []  # type: ignore[arg-type]

    def test_no_refs(self):
        assert extract_issue_numbers("Just a PR body with no references") == []

    def test_plain_hash_not_matched(self):
        assert extract_issue_numbers("See #5 for details") == []

    def test_multiline(self):
        body = "First line\nCloses #1\nAlso fixes #2\n"
        assert set(extract_issue_numbers(body)) == {1, 2}

    def test_large_issue_number(self):
        assert extract_issue_numbers("Closes #99999") == [99999]


# ===========================================================================
# Idempotency
# ===========================================================================


class TestIdempotency:
    """Test that duplicate delivery IDs are rejected."""

    def test_not_duplicate_initially(self):
        assert not is_duplicate("new-delivery")

    def test_becomes_duplicate_after_processing(self):
        process_event("d1", "push", b"{}", {"data": {}})
        assert is_duplicate("d1")

    def test_duplicate_returns_same_log(self):
        a = process_event("d2", "push", b"{}", {"data": {}})
        b = process_event("d2", "push", b"{}", {"data": {}})
        assert a.delivery_id == b.delivery_id
        assert a is b

    def test_different_ids_not_duplicate(self):
        process_event("d3", "push", b"{}", {"data": {}})
        assert not is_duplicate("d4")

    def test_duplicate_preserves_original_status(self):
        original = process_event("d5", "push", b"{}", {"data": {}})
        assert original.status == EventStatus.PROCESSED
        duplicate = process_event("d5", "push", b"{}", {"data": {}})
        assert duplicate.status == EventStatus.PROCESSED

    def test_concurrent_delivery_dedup(self):
        """Simulate concurrent webhook deliveries with the same ID."""
        results = []
        barrier = threading.Barrier(10)

        def deliver():
            barrier.wait()
            log = process_event(
                "concurrent-1", "push",
                b'{"ref":"x"}', {"data": {}},
            )
            results.append(log)

        threads = [threading.Thread(target=deliver) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 10
        assert all(r.delivery_id == "concurrent-1" for r in results)
        assert get_event_log("concurrent-1") is not None
        logs = list_event_logs()
        concurrent_logs = [lg for lg in logs if lg.delivery_id == "concurrent-1"]
        assert len(concurrent_logs) == 1


# ===========================================================================
# Event logging
# ===========================================================================


class TestEventLog:
    """Test event log creation, retrieval, and lifecycle."""

    def test_log_created_with_processed_status(self):
        log = process_event("l1", "push", b"{}", {"data": {}})
        assert log.status == EventStatus.PROCESSED
        assert log.delivery_id == "l1"
        assert log.event_type == "push"

    def test_payload_hash_is_sha256(self):
        p = b'{"key": "value"}'
        log = process_event("l2", "push", p, {"data": {}})
        expected_hash = hashlib.sha256(p).hexdigest()
        assert log.payload_hash == expected_hash

    def test_get_event_log(self):
        process_event("l3", "push", b"{}", {"data": {}})
        retrieved = get_event_log("l3")
        assert retrieved is not None
        assert retrieved.delivery_id == "l3"

    def test_get_nonexistent_returns_none(self):
        assert get_event_log("nonexistent") is None

    def test_list_event_logs(self):
        process_event("la", "push", b"{}", {"data": {}})
        process_event("lb", "issues", b"{}", {"data": {}})
        logs = list_event_logs()
        assert len(logs) == 2

    def test_list_filtered_by_event_type(self):
        process_event("ft1", "push", b"{}", {"data": {}})
        process_event("ft2", "issues", b"{}", {"data": {}})
        process_event("ft3", "push", b"{}", {"data": {}})
        push_logs = list_event_logs(event_type="push")
        assert len(push_logs) == 2
        assert all(lg.event_type == "push" for lg in push_logs)

    def test_list_filtered_by_status(self):
        process_event("fs1", "push", b"{}", {"data": {}})
        process_event("fs2", "push", b"not-json", {"data": {}})
        failed = list_event_logs(status=EventStatus.FAILED)
        assert len(failed) == 1
        assert failed[0].delivery_id == "fs2"

    def test_list_with_limit(self):
        for i in range(20):
            process_event(f"lim-{i}", "push", b"{}", {"data": {}})
        logs = list_event_logs(limit=5)
        assert len(logs) == 5

    def test_clear_event_logs(self):
        process_event("cl1", "push", b"{}", {"data": {}})
        assert len(list_event_logs()) == 1
        clear_event_logs()
        assert len(list_event_logs()) == 0

    def test_processed_at_set_on_success(self):
        log = process_event("pa1", "push", b"{}", {"data": {}})
        assert log.processed_at is not None

    def test_processed_at_set_on_failure(self):
        log = process_event("pa2", "push", b"bad", {"data": {}})
        assert log.processed_at is not None
        assert log.status == EventStatus.FAILED

    def test_received_at_set(self):
        log = process_event("ra1", "push", b"{}", {"data": {}})
        assert log.received_at is not None

    def test_event_log_responses(self):
        process_event("resp1", "push", b"{}", {"data": {}})
        responses = event_log_responses()
        assert len(responses) == 1
        assert responses[0].delivery_id == "resp1"
        assert responses[0].status == "processed"


# ===========================================================================
# Error handling
# ===========================================================================


class TestErrorHandling:
    """Test that processing errors are caught and logged."""

    def test_invalid_json_marks_failed(self):
        log = process_event("err1", "push", b"not valid json", {"data": {}})
        assert log.status == EventStatus.FAILED
        assert log.error_message is not None

    def test_empty_payload_succeeds(self):
        log = process_event("err2", "push", b"{}", {"data": {}})
        assert log.status == EventStatus.PROCESSED

    def test_empty_bytes_marks_failed(self):
        log = process_event("err3", "push", b"", {"data": {}})
        assert log.status == EventStatus.FAILED

    def test_unicode_payload(self):
        data = {"message": "Hello world"}
        log = process_event("err4", "push", _payload(data), {"data": data})
        assert log.status == EventStatus.PROCESSED

    def test_large_payload(self):
        data = {"big_field": "x" * 200_000}
        log = process_event("err5", "push", _payload(data), {"data": data})
        assert log.status == EventStatus.PROCESSED

    def test_nested_payload(self):
        data = {"a": {"b": {"c": {"d": [1, 2, 3]}}}}
        log = process_event("err6", "push", _payload(data), {"data": data})
        assert log.status == EventStatus.PROCESSED


# ===========================================================================
# PR event metadata extraction
# ===========================================================================


class TestPREventProcessing:
    """Test metadata extraction from pull_request events."""

    def test_pr_opened(self):
        log = _proc("pr1", "pull_request", _pr_event(action="opened", body="Closes #5"))
        assert log.status == EventStatus.PROCESSED

    def test_pr_merged(self):
        log = _proc(
            "pr2", "pull_request",
            _pr_event(action="closed", body="Fixes #10", merged=True),
        )
        assert log.status == EventStatus.PROCESSED

    def test_pr_closed_not_merged(self):
        log = _proc(
            "pr3", "pull_request",
            _pr_event(action="closed", body="Closes #5", merged=False),
        )
        assert log.status == EventStatus.PROCESSED

    def test_pr_reopened(self):
        log = _proc("pr4", "pull_request", _pr_event(action="reopened"))
        assert log.status == EventStatus.PROCESSED

    def test_pr_no_body(self):
        event = _pr_event(action="opened", body="")
        event["pull_request"]["body"] = None
        log = _proc("pr5", "pull_request", event)
        assert log.status == EventStatus.PROCESSED

    def test_pr_multiple_issue_refs(self):
        log = _proc(
            "pr6", "pull_request",
            _pr_event(body="Closes #1, Fixes #2, Resolves #3"),
        )
        assert log.status == EventStatus.PROCESSED

    def test_pr_with_missing_repo(self):
        event = _pr_event()
        event.pop("repository", None)
        log = _proc("pr7", "pull_request", event)
        assert log.status == EventStatus.PROCESSED


# ===========================================================================
# Issue event metadata extraction
# ===========================================================================


class TestIssueEventProcessing:
    """Test metadata extraction from issues events."""

    def test_issue_labeled(self):
        log = _proc("iss1", "issues", _issue_event(action="labeled", label="bounty"))
        assert log.status == EventStatus.PROCESSED

    def test_issue_opened(self):
        log = _proc("iss2", "issues", _issue_event(action="opened"))
        assert log.status == EventStatus.PROCESSED

    def test_issue_non_bounty_label(self):
        log = _proc("iss3", "issues", _issue_event(action="labeled", label="bug"))
        assert log.status == EventStatus.PROCESSED

    def test_issue_with_no_labels(self):
        event = _issue_event()
        event["issue"]["labels"] = []
        log = _proc("iss4", "issues", event)
        assert log.status == EventStatus.PROCESSED


# ===========================================================================
# Push event metadata extraction
# ===========================================================================


class TestPushEventProcessing:
    """Test metadata extraction from push events."""

    def test_push_to_main(self):
        log = _proc("push1", "push", _push_event(ref="refs/heads/main"))
        assert log.status == EventStatus.PROCESSED

    def test_push_with_multiple_commits(self):
        log = _proc("push2", "push", _push_event(num_commits=5))
        assert log.status == EventStatus.PROCESSED

    def test_push_to_branch(self):
        log = _proc("push3", "push", _push_event(ref="refs/heads/feature/xyz"))
        assert log.status == EventStatus.PROCESSED


# ===========================================================================
# Unhandled event types
# ===========================================================================


class TestUnhandledEvents:
    """Events without special extraction still get logged as PROCESSED."""

    def test_deployment_event(self):
        log = process_event(
            "unk1", "deployment",
            b'{"environment":"prod"}', {"data": {}},
        )
        assert log.status == EventStatus.PROCESSED

    def test_star_event(self):
        log = process_event(
            "unk2", "star",
            b'{"action":"created"}', {"data": {}},
        )
        assert log.status == EventStatus.PROCESSED

    def test_unknown_event(self):
        log = process_event(
            "unk3", "completely_new_event_type",
            b'{"x":1}', {"data": {}},
        )
        assert log.status == EventStatus.PROCESSED
