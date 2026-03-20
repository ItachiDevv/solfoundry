"""Tests for bounty completion and review flow."""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.models.bounty import BountyCreate, BountyTier
from app.models.review import ModelScore
from app.services import bounty_service, review_service
from app.services.payout_service import _payout_store
from app.api.reviews import router

_a = FastAPI()
_a.include_router(router)
c = TestClient(_a)
PR = "https://github.com/SolFoundry/solfoundry/pull/191"
W = "97VihHW2Br7BKUU16c7RxjiEMHsD4dWisGDT2Y3LyJxF"


@pytest.fixture(autouse=True)
def _reset():
    for s in [bounty_service._bounty_store, review_service._review_store, _payout_store]:
        s.clear()
    yield
    for s in [bounty_service._bounty_store, review_service._review_store, _payout_store]:
        s.clear()


def _b(tier=2, reward=500000.0):
    return bounty_service.create_bounty(BountyCreate(title="Test", description="d",
        tier=BountyTier(tier), reward_amount=reward, created_by="creator")).id


def _sc():
    return [{"model_name": m, "quality": 8, "correctness": 8.5, "security": 9,
             "completeness": 7.5, "tests": 7.5, "integration": 8} for m in ("gpt", "gemini", "grok")]


def _sub(bid, pr=PR):
    return c.post(f"/api/reviews/bounties/{bid}/submit",
                  json={"pr_url": pr, "contributor_wallet": W, "submitted_by": "dev1"})


def _sco(bid, s=None):
    return c.post(f"/api/reviews/bounties/{bid}/scores", json={"scores": s or _sc()})


def _ready(tier=2):
    bid = _b(tier=tier); _sub(bid); _sco(bid); return bid


class TestSubmit:
    def test_ok(self):
        bid = _b(); r = _sub(bid)
        assert r.status_code == 201 and r.json()["status"] == "in_review"

    def test_404(self):
        assert _sub("x").status_code == 404

    def test_dup(self):
        bid = _b(); _sub(bid); assert _sub(bid).status_code == 400

    def test_bad_url(self):
        bid = _b()
        assert c.post(f"/api/reviews/bounties/{bid}/submit", json={
            "pr_url": "https://gitlab.com/x/pull/1", "contributor_wallet": W, "submitted_by": "d"
        }).status_code == 422


class TestScores:
    def test_ok(self):
        bid = _b(); _sub(bid); r = _sco(bid)
        assert r.json()["status"] == "scored" and r.json()["overall_score"] > 0

    def test_404(self):
        assert _sco(_b()).status_code == 404

    def test_breakdown(self):
        bid = _b(); _sub(bid)
        for s in _sco(bid).json()["scores"]:
            assert all(k in s for k in ("quality", "correctness", "security"))

    def test_dup_model(self):
        bid = _b(); _sub(bid)
        dup = [{"model_name": "gpt", "quality": 8, "correctness": 8, "security": 8,
                "completeness": 8, "tests": 8, "integration": 8}] * 2
        assert c.post(f"/api/reviews/bounties/{bid}/scores", json={"scores": dup}).status_code == 422

    def test_threshold(self):
        bid = _b(); _sub(bid); assert _sco(bid).json()["meets_threshold"] is True
        bid2 = _b(); _sub(bid2)
        lo = [{"model_name": "gpt", "quality": 4, "correctness": 4, "security": 5,
               "completeness": 3, "tests": 3, "integration": 4}]
        assert _sco(bid2, lo).json()["meets_threshold"] is False


class TestApprove:
    def test_ok(self):
        bid = _ready()
        d = c.post(f"/api/reviews/bounties/{bid}/approve", json={"approved_by": "c"}).json()
        assert d["status"] == "paid" and d["payout_amount"] == 500000.0 and d["winner_wallet"] == W
        assert len(_payout_store) == 1

    def test_404(self):
        assert c.post(f"/api/reviews/bounties/{_b()}/approve",
                      json={"approved_by": "c"}).status_code == 404

    def test_double(self):
        bid = _ready()
        c.post(f"/api/reviews/bounties/{bid}/approve", json={"approved_by": "c"})
        assert c.post(f"/api/reviews/bounties/{bid}/approve",
                      json={"approved_by": "c"}).status_code == 400


class TestDispute:
    def test_ok(self):
        bid = _ready()
        assert c.post(f"/api/reviews/bounties/{bid}/dispute",
            json={"disputed_by": "c", "reason": "Does not match requirements"}).json()["status"] == "disputed"

    def test_blocks_approve(self):
        bid = _ready()
        c.post(f"/api/reviews/bounties/{bid}/dispute",
               json={"disputed_by": "c", "reason": "Incomplete implementation"})
        assert c.post(f"/api/reviews/bounties/{bid}/approve",
                      json={"approved_by": "c"}).status_code == 400

    def test_404(self):
        assert c.post(f"/api/reviews/bounties/{_b()}/dispute",
            json={"disputed_by": "c", "reason": "Valid reason here"}).status_code == 404

    def test_short_reason(self):
        bid = _ready()
        assert c.post(f"/api/reviews/bounties/{bid}/dispute",
                      json={"disputed_by": "c", "reason": "bad"}).status_code == 422


class TestGetList:
    def test_get_and_404(self):
        bid = _b(); _sub(bid)
        assert c.get(f"/api/reviews/bounties/{bid}").status_code == 200
        assert c.get("/api/reviews/bounties/x").status_code == 404

    def test_list(self):
        assert c.get("/api/reviews").json() == []
        bid = _b(); _sub(bid)
        assert len(c.get("/api/reviews?status=in_review").json()) == 1


class TestAutoApprove:
    def test_eligible(self):
        _ready()
        list(review_service._review_store.values())[0].scored_at = (
            datetime.now(timezone.utc) - timedelta(hours=49))
        assert c.post("/api/reviews/auto-approve").json()["approved_count"] == 1

    def test_recent(self):
        _ready(); assert c.post("/api/reviews/auto-approve").json()["approved_count"] == 0

    def test_low_skipped(self):
        bid = _b(); _sub(bid)
        lo = [{"model_name": "gpt", "quality": 4, "correctness": 4, "security": 5,
               "completeness": 3, "tests": 3, "integration": 4}]
        _sco(bid, lo)
        list(review_service._review_store.values())[0].scored_at = (
            datetime.now(timezone.utc) - timedelta(hours=49))
        assert c.post("/api/reviews/auto-approve").json()["approved_count"] == 0

    def test_empty(self):
        assert c.post("/api/reviews/auto-approve").json()["checked_count"] == 0


class TestLifecycle:
    def test_full_log(self):
        bid = _ready()
        c.post(f"/api/reviews/bounties/{bid}/approve", json={"approved_by": "c"})
        actions = [e["action"] for e in c.get(f"/api/reviews/bounties/{bid}").json()["lifecycle_log"]]
        assert "PR submitted for review" in actions
        assert any("scored" in a for a in actions)

    def test_winner(self):
        bid = _b(reward=750000.0); _sub(bid); _sco(bid)
        c.post(f"/api/reviews/bounties/{bid}/approve", json={"approved_by": "c"})
        d = c.get(f"/api/reviews/bounties/{bid}").json()
        assert d["winner_wallet"] == W and d["payout_amount"] == 750000.0


class TestModelScoreCalc:
    def test_avg(self):
        s = ModelScore(model_name="g", quality=8, correctness=9, security=9.5,
                       completeness=7, tests=7.5, integration=8)
        assert s.compute_average() == round((8+9+9.5+7+7.5+8)/6, 2)

    def test_extremes(self):
        mx = ModelScore(model_name="g", quality=10, correctness=10, security=10,
                        completeness=10, tests=10, integration=10)
        mn = ModelScore(model_name="g", quality=0, correctness=0, security=0,
                        completeness=0, tests=0, integration=0)
        assert mx.compute_average() == 10.0 and mn.compute_average() == 0.0
