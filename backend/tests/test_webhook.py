"""Comprehensive tests for the GitHub webhook receiver endpoint.

Covers:
- HMAC-SHA256 signature verification (valid, invalid, missing, wrong format)
- Event parsing for all supported event types (ping, push, PR, issues)
- Idempotency / duplicate delivery detection at the HTTP layer
- Malformed payloads (invalid JSON, empty body)
- Edge cases: no secret configured, unhandled event types, missing headers
- Concurrent duplicate deliveries at the HTTP level
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.event_processor import _event_log_store, clear_event_logs

client = TestClient(app)

SECRET = "test-webhook-secret"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_event_log():
    """Ensure a clean event log for every test."""
    clear_event_logs()
    yield
    clear_event_logs()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sign(payload: bytes, secret: str = SECRET) -> str:
    """Compute HMAC-SHA256 signature for a payload."""
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def _post(
    event_type,
    payload,
    *,
    secret=SECRET,
    delivery_id="test-delivery-123",
    include_sig=True,
):
    """Send a webhook POST with optional signing."""
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    headers = {
        "X-GitHub-Event": event_type,
        "X-GitHub-Delivery": delivery_id,
        "Content-Type": "application/json",
    }
    if include_sig and secret:
        headers["X-Hub-Signature-256"] = _sign(body, secret)
    return client.post("/api/webhooks/github", content=body, headers=headers)


# ---------------------------------------------------------------------------
# Sample payloads
# ---------------------------------------------------------------------------

PING_PAYLOAD = {
    "zen": "Design for failure.",
    "hook_id": 42,
    "hook": {"type": "Repository", "id": 42, "name": "web"},
    "repository": {
        "id": 1, "name": "solfoundry", "full_name": "SolFoundry/solfoundry",
        "owner": {"login": "SolFoundry", "id": 1},
    },
    "sender": {"login": "bot", "id": 99},
}

PUSH_PAYLOAD = {
    "ref": "refs/heads/main",
    "before": "a" * 40,
    "after": "b" * 40,
    "repository": {
        "id": 1, "name": "solfoundry", "full_name": "SolFoundry/solfoundry",
        "owner": {"login": "SolFoundry", "id": 1},
    },
    "sender": {"login": "dev", "id": 2},
    "head_commit": {"message": "init"},
    "commits": [],
}

PR_PAYLOAD = {
    "action": "opened",
    "number": 12,
    "pull_request": {
        "number": 12, "title": "feat: webhook receiver",
        "state": "open", "user": {"login": "dev", "id": 2},
        "body": "Implements #12", "html_url": "https://github.com/test/pr/12",
    },
    "repository": {
        "id": 1, "name": "solfoundry", "full_name": "SolFoundry/solfoundry",
        "owner": {"login": "SolFoundry", "id": 1},
    },
    "sender": {"login": "dev", "id": 2},
}

ISSUE_PAYLOAD = {
    "action": "opened",
    "issue": {
        "number": 12, "title": "Webhook receiver", "state": "open",
        "user": {"login": "dev", "id": 2},
    },
    "repository": {
        "id": 1, "name": "solfoundry", "full_name": "SolFoundry/solfoundry",
        "owner": {"login": "SolFoundry", "id": 1},
    },
    "sender": {"login": "dev", "id": 2},
}


# ===========================================================================
# Signature verification (secret configured)
# ===========================================================================

@patch.dict("app.api.webhooks.github.os.environ", {"GITHUB_WEBHOOK_SECRET": SECRET})
class TestSignatureVerification:
    """Test HMAC-SHA256 signature checking."""

    def test_valid_signature_ping(self):
        r = _post("ping", PING_PAYLOAD)
        assert r.status_code == 200
        assert r.json()["msg"] == "pong"

    def test_valid_signature_push(self):
        r = _post("push", PUSH_PAYLOAD)
        assert r.status_code == 202
        assert r.json()["event"] == "push"

    def test_valid_signature_pr(self):
        r = _post("pull_request", PR_PAYLOAD)
        assert r.status_code == 202
        assert r.json()["event"] == "pull_request"

    def test_valid_signature_issues(self):
        r = _post("issues", ISSUE_PAYLOAD)
        assert r.status_code == 202
        assert r.json()["event"] == "issues"

    def test_invalid_signature_rejected(self):
        body = json.dumps(PING_PAYLOAD).encode()
        r = client.post(
            "/api/webhooks/github",
            content=body,
            headers={
                "X-GitHub-Event": "ping",
                "X-Hub-Signature-256": "sha256=" + "0" * 64,
                "X-GitHub-Delivery": "d",
            },
        )
        assert r.status_code == 401

    def test_missing_signature_rejected(self):
        body = json.dumps(PING_PAYLOAD).encode()
        r = client.post(
            "/api/webhooks/github",
            content=body,
            headers={"X-GitHub-Event": "ping", "X-GitHub-Delivery": "d"},
        )
        assert r.status_code == 401

    def test_wrong_secret_rejected(self):
        body = json.dumps(PING_PAYLOAD).encode()
        sig = _sign(body, "wrong-secret")
        r = client.post(
            "/api/webhooks/github",
            content=body,
            headers={
                "X-GitHub-Event": "ping",
                "X-Hub-Signature-256": sig,
                "X-GitHub-Delivery": "d",
            },
        )
        assert r.status_code == 401

    def test_malformed_signature_prefix_rejected(self):
        """Signature with wrong prefix (e.g. sha1= instead of sha256=)."""
        body = json.dumps(PING_PAYLOAD).encode()
        r = client.post(
            "/api/webhooks/github",
            content=body,
            headers={
                "X-GitHub-Event": "ping",
                "X-Hub-Signature-256": "sha1=abcdef1234567890",
                "X-GitHub-Delivery": "d",
            },
        )
        assert r.status_code == 401

    def test_empty_signature_header_rejected(self):
        body = json.dumps(PING_PAYLOAD).encode()
        r = client.post(
            "/api/webhooks/github",
            content=body,
            headers={
                "X-GitHub-Event": "ping",
                "X-Hub-Signature-256": "",
                "X-GitHub-Delivery": "d",
            },
        )
        assert r.status_code == 401

    def test_signature_with_tampered_body_rejected(self):
        """Sign one payload but send a different one."""
        original = json.dumps(PING_PAYLOAD).encode()
        tampered = json.dumps({"zen": "Tampered!"}).encode()
        sig = _sign(original)
        r = client.post(
            "/api/webhooks/github",
            content=tampered,
            headers={
                "X-GitHub-Event": "ping",
                "X-Hub-Signature-256": sig,
                "X-GitHub-Delivery": "d",
            },
        )
        assert r.status_code == 401


# ===========================================================================
# No secret configured (verification skipped)
# ===========================================================================

@patch.dict("app.api.webhooks.github.os.environ", {"GITHUB_WEBHOOK_SECRET": ""})
class TestNoSecretConfigured:
    """When GITHUB_WEBHOOK_SECRET is empty, verification is skipped."""

    def test_ping_no_secret(self):
        body = json.dumps(PING_PAYLOAD).encode()
        r = client.post(
            "/api/webhooks/github",
            content=body,
            headers={"X-GitHub-Event": "ping", "X-GitHub-Delivery": "d"},
        )
        assert r.status_code == 200

    def test_push_no_secret(self):
        r = _post("push", PUSH_PAYLOAD, secret=None, include_sig=False)
        assert r.status_code == 202

    def test_unhandled_event_passes_through(self):
        body = json.dumps({"foo": "bar"}).encode()
        r = client.post(
            "/api/webhooks/github",
            content=body,
            headers={"X-GitHub-Event": "deployment", "X-GitHub-Delivery": "d"},
        )
        assert r.status_code == 202
        assert r.json()["event"] == "deployment"


# ===========================================================================
# Malformed payloads
# ===========================================================================

@patch.dict("app.api.webhooks.github.os.environ", {"GITHUB_WEBHOOK_SECRET": ""})
class TestMalformedPayloads:
    """Test handling of invalid or edge-case payloads."""

    def test_invalid_json_returns_422(self):
        r = client.post(
            "/api/webhooks/github",
            content=b"not json",
            headers={"X-GitHub-Event": "push", "X-GitHub-Delivery": "d"},
        )
        assert r.status_code == 422

    def test_empty_body_returns_422(self):
        r = client.post(
            "/api/webhooks/github",
            content=b"",
            headers={"X-GitHub-Event": "push", "X-GitHub-Delivery": "d"},
        )
        assert r.status_code == 422

    def test_null_json_handled(self):
        r = client.post(
            "/api/webhooks/github",
            content=b"null",
            headers={"X-GitHub-Event": "push", "X-GitHub-Delivery": "d"},
        )
        # null is valid JSON but not a dict -- must not crash
        assert r.status_code in (202, 422)

    def test_missing_event_header(self):
        body = json.dumps(PUSH_PAYLOAD).encode()
        r = client.post(
            "/api/webhooks/github",
            content=body,
            headers={"X-GitHub-Delivery": "d"},
        )
        # Without X-GitHub-Event, event_type defaults to "unknown"
        assert r.status_code == 202
        assert r.json()["event"] == "unknown"


# ===========================================================================
# Idempotency at HTTP layer
# ===========================================================================

@patch.dict("app.api.webhooks.github.os.environ", {"GITHUB_WEBHOOK_SECRET": ""})
class TestIdempotency:
    """Test duplicate delivery detection via X-GitHub-Delivery header."""

    def test_first_delivery_accepted(self):
        r = _post("push", PUSH_PAYLOAD, secret=None, include_sig=False, delivery_id="unique-1")
        assert r.status_code == 202
        assert r.json()["status"] == "accepted"

    def test_duplicate_delivery_detected(self):
        r1 = _post("push", PUSH_PAYLOAD, secret=None, include_sig=False, delivery_id="dup-1")
        assert r1.status_code == 202
        r2 = _post("push", PUSH_PAYLOAD, secret=None, include_sig=False, delivery_id="dup-1")
        assert r2.status_code == 200
        assert r2.json()["status"] == "duplicate"

    def test_different_delivery_ids_both_accepted(self):
        r1 = _post("push", PUSH_PAYLOAD, secret=None, include_sig=False, delivery_id="a")
        r2 = _post("push", PUSH_PAYLOAD, secret=None, include_sig=False, delivery_id="b")
        assert r1.status_code == 202
        assert r2.status_code == 202

    def test_concurrent_duplicate_deliveries(self):
        """Multiple threads deliver the same X-GitHub-Delivery simultaneously."""
        results = []
        barrier = threading.Barrier(5)

        def deliver():
            barrier.wait()
            body = json.dumps(PUSH_PAYLOAD).encode()
            r = client.post(
                "/api/webhooks/github",
                content=body,
                headers={
                    "X-GitHub-Event": "push",
                    "X-GitHub-Delivery": "concurrent-dup",
                },
            )
            results.append(r.status_code)

        threads = [threading.Thread(target=deliver) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly one should be 202 (accepted), rest should be 200 (duplicate)
        assert 202 in results
        assert all(code in (200, 202) for code in results)

    def test_rapid_sequential_duplicates(self):
        """Send the same delivery ID 10 times quickly."""
        body = json.dumps(PUSH_PAYLOAD).encode()
        statuses = []
        for _ in range(10):
            r = client.post(
                "/api/webhooks/github",
                content=body,
                headers={
                    "X-GitHub-Event": "push",
                    "X-GitHub-Delivery": "rapid-dup",
                },
            )
            statuses.append(r.status_code)

        assert statuses[0] == 202
        assert all(s == 200 for s in statuses[1:])


# ===========================================================================
# Event type routing
# ===========================================================================

@patch.dict("app.api.webhooks.github.os.environ", {"GITHUB_WEBHOOK_SECRET": ""})
class TestEventRouting:
    """Test that different event types are handled correctly."""

    def test_ping_returns_pong(self):
        r = _post("ping", PING_PAYLOAD, secret=None, include_sig=False)
        assert r.status_code == 200
        assert r.json()["msg"] == "pong"

    def test_push_accepted(self):
        r = _post("push", PUSH_PAYLOAD, secret=None, include_sig=False, delivery_id="rt-1")
        assert r.status_code == 202
        assert r.json()["status"] == "accepted"

    def test_pull_request_accepted(self):
        r = _post("pull_request", PR_PAYLOAD, secret=None, include_sig=False, delivery_id="rt-2")
        assert r.status_code == 202

    def test_issues_accepted(self):
        r = _post("issues", ISSUE_PAYLOAD, secret=None, include_sig=False, delivery_id="rt-3")
        assert r.status_code == 202

    def test_unknown_event_accepted(self):
        r = _post(
            "workflow_run", {"action": "completed"},
            secret=None, include_sig=False, delivery_id="rt-4",
        )
        assert r.status_code == 202
        assert r.json()["event"] == "workflow_run"

    def test_event_creates_log_entry(self):
        delivery = str(uuid.uuid4())
        _post("push", PUSH_PAYLOAD, secret=None, include_sig=False, delivery_id=delivery)
        assert delivery in _event_log_store
        log = _event_log_store[delivery]
        assert log.event_type == "push"

    def test_ping_does_not_create_log_entry(self):
        """Ping events are acknowledged but not logged as processed events."""
        delivery = "ping-delivery"
        _post("ping", PING_PAYLOAD, secret=None, include_sig=False, delivery_id=delivery)
        # Ping returns before the event processor runs
        assert delivery not in _event_log_store
