"""Tests for the webhook event processing pipeline."""

from __future__ import annotations

import hashlib
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.bounty import BountyCreate, BountyDB, BountyStatus, BountyTier
from app.models.event_log import EventStatus
from app.services.bounty_service import _bounty_store, create_bounty
from app.services.bounty_status_service import (
    auto_create_bounty_from_issue,
    find_bounty_by_issue_number,
    transition_to_completed,
    transition_to_in_progress,
)
from app.services.event_processor import (
    clear_event_logs,
    extract_issue_numbers,
    get_event_log,
    is_duplicate,
    list_event_logs,
    process_event,
)

client = TestClient(app)
REPO = "SolFoundry/solfoundry"


@pytest.fixture(autouse=True)
def _clean():
    _bounty_store.clear()
    clear_event_logs()
    yield
    _bounty_store.clear()
    clear_event_logs()


def _bounty(n, status=BountyStatus.OPEN):
    r = create_bounty(BountyCreate(
        title=f"Bounty #{n}", description="d", tier=BountyTier.T1,
        reward_amount=100.0, github_issue_url=f"https://github.com/{REPO}/issues/{n}",
    ))
    b = _bounty_store[r.id]
    b.status = status
    return b


def _pr(action="opened", body="Closes #5", num=10, merged=False):
    return {
        "action": action, "number": num,
        "pull_request": {"number": num, "title": "Fix", "state": "closed" if action == "closed" else "open",
                         "user": {"login": "d", "id": 2}, "body": body, "merged": merged},
        "repository": {"id": 1, "name": "s", "full_name": REPO, "owner": {"login": "S", "id": 1}},
        "sender": {"login": "d", "id": 2},
    }


def _issue_lbl(n=5, lbl="bounty"):
    return {
        "action": "labeled", "label": {"id": 1, "name": lbl},
        "issue": {"number": n, "title": f"I#{n}", "body": "T", "state": "open",
                  "user": {"login": "d", "id": 2}, "labels": [{"id": 1, "name": lbl}]},
        "repository": {"id": 1, "name": "s", "full_name": REPO, "owner": {"login": "S", "id": 1}},
        "sender": {"login": "d", "id": 2},
    }


def _proc(did, etype, d):
    p = json.dumps(d).encode()
    return process_event(did, etype, p, {"data": d})


# -- extract_issue_numbers --
class TestExtract:
    def test_closes(self): assert extract_issue_numbers("Closes #5") == [5]
    def test_fixes(self): assert extract_issue_numbers("Fixes #12") == [12]
    def test_resolves(self): assert extract_issue_numbers("Resolves #42") == [42]
    def test_case(self): assert extract_issue_numbers("CLOSES #5") == [5]
    def test_multi(self): assert set(extract_issue_numbers("Closes #5, Fixes #12")) == {5, 12}
    def test_none(self): assert extract_issue_numbers("") == []
    def test_closed(self): assert extract_issue_numbers("Closed #7") == [7]
    def test_fixed(self): assert extract_issue_numbers("Fixed #8") == [8]
    def test_resolved(self): assert extract_issue_numbers("Resolved #9") == [9]
    def test_norefs(self): assert extract_issue_numbers("Just a PR body") == []


# -- idempotency --
class TestIdemp:
    def test_not_dup(self): assert not is_duplicate("x")
    def test_dup(self):
        process_event("d1", "push", b"{}", {"data": {}})
        assert is_duplicate("d1")
    def test_same(self):
        a = process_event("d2", "push", b"{}", {"data": {}})
        b = process_event("d2", "push", b"{}", {"data": {}})
        assert a.delivery_id == b.delivery_id


# -- event log --
class TestLog:
    def test_created(self):
        log = process_event("l1", "push", b"{}", {"data": {}})
        assert log.status == EventStatus.PROCESSED
    def test_hash(self):
        p = b'{"a":1}'
        log = process_event("l2", "push", p, {"data": {}})
        assert log.payload_hash == hashlib.sha256(p).hexdigest()
    def test_get(self):
        process_event("l3", "push", b"{}", {"data": {}})
        assert get_event_log("l3") is not None
    def test_list(self):
        process_event("la", "push", b"{}", {"data": {}})
        process_event("lb", "push", b"{}", {"data": {}})
        assert len(list_event_logs()) == 2
    def test_clear(self):
        process_event("lc", "push", b"{}", {"data": {}})
        clear_event_logs()
        assert len(list_event_logs()) == 0


# -- PR opened -> in_progress --
class TestPROpen:
    def test_open(self):
        b = _bounty(5)
        log = _proc("po1", "pull_request", _pr(action="opened", body="Closes #5"))
        assert log.status == EventStatus.PROCESSED
        assert b.status == BountyStatus.IN_PROGRESS

    def test_idempotent(self):
        b = _bounty(6, BountyStatus.IN_PROGRESS)
        _proc("po2", "pull_request", _pr(action="opened", body="Fixes #6", num=11))
        assert b.status == BountyStatus.IN_PROGRESS

    def test_no_bounty(self):
        log = _proc("po3", "pull_request", _pr(action="opened", body="Closes #999"))
        assert log.status == EventStatus.PROCESSED

    def test_no_closes(self):
        log = _proc("po4", "pull_request", _pr(action="opened", body="Just a PR"))
        assert log.status == EventStatus.PROCESSED

    def test_reopened(self):
        b = _bounty(7)
        _proc("po5", "pull_request", _pr(action="reopened", body="Closes #7"))
        assert b.status == BountyStatus.IN_PROGRESS


# -- PR merged -> completed --
class TestPRMerge:
    def test_merged(self):
        b = _bounty(5, BountyStatus.IN_PROGRESS)
        log = _proc("pm1", "pull_request", _pr(action="closed", body="Closes #5", merged=True))
        assert log.status == EventStatus.PROCESSED
        assert b.status == BountyStatus.COMPLETED

    def test_closed_no_merge(self):
        b = _bounty(5, BountyStatus.IN_PROGRESS)
        _proc("pm2", "pull_request", _pr(action="closed", body="Closes #5", merged=False))
        assert b.status == BountyStatus.IN_PROGRESS

    def test_multi_refs(self):
        b1 = _bounty(5, BountyStatus.IN_PROGRESS)
        b2 = _bounty(6, BountyStatus.IN_PROGRESS)
        _proc("pm3", "pull_request", _pr(action="closed", body="Closes #5, Fixes #6", merged=True))
        assert b1.status == BountyStatus.COMPLETED
        assert b2.status == BountyStatus.COMPLETED


# -- Issue labeled bounty --
class TestIssueLbl:
    def test_creates(self):
        log = _proc("il1", "issues", _issue_lbl(n=20))
        assert log.status == EventStatus.PROCESSED
        assert find_bounty_by_issue_number(20, REPO) is not None

    def test_no_dup(self):
        _bounty(21)
        _proc("il2", "issues", _issue_lbl(n=21))
        assert len([b for b in _bounty_store.values() if b.github_issue_url and "issues/21" in b.github_issue_url]) == 1

    def test_non_bounty(self):
        _proc("il3", "issues", _issue_lbl(n=22, lbl="bug"))
        assert find_bounty_by_issue_number(22, REPO) is None

    def test_not_labeled(self):
        d = _issue_lbl(n=23)
        d["action"] = "opened"
        _proc("il4", "issues", d)
        assert find_bounty_by_issue_number(23, REPO) is None


# -- bounty_status_service --
class TestStatusSvc:
    def test_find(self):
        _bounty(30)
        assert find_bounty_by_issue_number(30, REPO) is not None

    def test_not_found(self):
        assert find_bounty_by_issue_number(9999, REPO) is None

    def test_to_ip(self):
        b = _bounty(31)
        assert transition_to_in_progress(b)
        assert b.status == BountyStatus.IN_PROGRESS

    def test_ip_from_done_fails(self):
        b = _bounty(32, BountyStatus.COMPLETED)
        assert not transition_to_in_progress(b)

    def test_to_done(self):
        b = _bounty(33, BountyStatus.IN_PROGRESS)
        assert transition_to_completed(b)
        assert b.status == BountyStatus.COMPLETED

    def test_done_from_open_fails(self):
        b = _bounty(34)
        assert not transition_to_completed(b)

    def test_auto_create(self):
        bid = auto_create_bounty_from_issue({"number": 40, "title": "New", "body": "C"}, REPO)
        assert bid is not None
        assert _bounty_store[bid].title == "New"

    def test_auto_dup(self):
        _bounty(41)
        assert auto_create_bounty_from_issue({"number": 41, "title": "D", "body": ""}, REPO) is None


# -- HTTP endpoint integration --
@patch.dict("app.api.webhooks.github.os.environ", {"GITHUB_WEBHOOK_SECRET": ""})
class TestEndpoint:
    def test_pr_opened(self):
        b = _bounty(50)
        r = client.post("/api/webhooks/github",
                        content=json.dumps(_pr(action="opened", body="Closes #50", num=100)).encode(),
                        headers={"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "e1"})
        assert r.status_code == 202
        assert b.status == BountyStatus.IN_PROGRESS

    def test_pr_merged(self):
        b = _bounty(51, BountyStatus.IN_PROGRESS)
        r = client.post("/api/webhooks/github",
                        content=json.dumps(_pr(action="closed", body="Closes #51", num=101, merged=True)).encode(),
                        headers={"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "e2"})
        assert r.status_code == 202
        assert b.status == BountyStatus.COMPLETED

    def test_duplicate(self):
        body = json.dumps(_pr(action="opened", body="Closes #52")).encode()
        r1 = client.post("/api/webhooks/github", content=body,
                         headers={"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "dup1"})
        assert r1.status_code == 202
        r2 = client.post("/api/webhooks/github", content=body,
                         headers={"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "dup1"})
        assert r2.status_code == 200
        assert r2.json()["status"] == "duplicate"

    def test_issue_labeled(self):
        r = client.post("/api/webhooks/github",
                        content=json.dumps(_issue_lbl(n=60)).encode(),
                        headers={"X-GitHub-Event": "issues", "X-GitHub-Delivery": "e3"})
        assert r.status_code == 202
        assert find_bounty_by_issue_number(60, REPO) is not None

    def test_event_log(self):
        client.post("/api/webhooks/github",
                    content=json.dumps(_pr(action="opened", body="Test")).encode(),
                    headers={"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "e4"})
        log = get_event_log("e4")
        assert log is not None
        assert log.status == EventStatus.PROCESSED
