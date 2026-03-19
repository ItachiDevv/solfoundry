"""Tests for the spam detection API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.services import spam_detector


@pytest.fixture(autouse=True)
def reset_stores():
    spam_detector._reset_stores()
    yield
    spam_detector._reset_stores()


@pytest.fixture
def client():
    # Import here to ensure middleware is loaded fresh
    # Disable rate limiting for API tests to avoid 429s
    import os
    os.environ["RATE_LIMIT_ENABLED"] = "false"
    from app.main import app
    return TestClient(app)


class TestSpamCheckEndpoint:
    def test_check_clean_pr(self, client):
        resp = client.post("/api/spam/check", json={
            "pr_number": 1,
            "pr_author": "alice",
            "pr_title": "Add feature",
            "diff": "+def hello(): return 'world'",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "is_spam" in data
        assert "total_penalty" in data
        assert "details" in data
        assert isinstance(data["details"], list)

    def test_check_requires_pr_number(self, client):
        resp = client.post("/api/spam/check", json={
            "pr_author": "alice",
        })
        assert resp.status_code == 422

    def test_check_requires_pr_author(self, client):
        resp = client.post("/api/spam/check", json={
            "pr_number": 1,
        })
        assert resp.status_code == 422

    def test_check_with_tier(self, client):
        resp = client.post("/api/spam/check", json={
            "pr_number": 1,
            "pr_author": "alice",
            "tier": "tier-3",
            "diff": "+code",
        })
        assert resp.status_code == 200


class TestSpamHistoryEndpoint:
    def test_empty_history(self, client):
        resp = client.get("/api/spam/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_history_after_checks(self, client):
        client.post("/api/spam/check", json={
            "pr_number": 1, "pr_author": "alice", "diff": "+code",
        })
        client.post("/api/spam/check", json={
            "pr_number": 2, "pr_author": "bob", "diff": "+more",
        })
        resp = client.get("/api/spam/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    def test_history_pagination(self, client):
        for i in range(5):
            client.post("/api/spam/check", json={
                "pr_number": i, "pr_author": f"user{i}", "diff": f"+code_{i}",
            })
        resp = client.get("/api/spam/history?skip=1&limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2


class TestSpamStatsEndpoint:
    def test_empty_stats(self, client):
        resp = client.get("/api/spam/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_checks"] == 0

    def test_stats_after_checks(self, client):
        client.post("/api/spam/check", json={
            "pr_number": 1, "pr_author": "alice", "diff": "+code",
        })
        resp = client.get("/api/spam/stats")
        data = resp.json()
        assert data["total_checks"] == 1


class TestSpamConfigEndpoint:
    def test_get_config(self, client):
        resp = client.get("/api/spam/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "velocity_max_prs_per_hour" in data
        assert "penalty_threshold_flag" in data

    def test_update_config_requires_auth(self, client):
        resp = client.patch("/api/spam/config", json={
            "velocity_max_prs_per_hour": 10,
        })
        assert resp.status_code == 401

    def test_update_config_wrong_key(self, client):
        resp = client.patch(
            "/api/spam/config",
            json={"velocity_max_prs_per_hour": 10},
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert resp.status_code == 403

    def test_update_config_success(self, client):
        resp = client.patch(
            "/api/spam/config",
            json={"velocity_max_prs_per_hour": 10},
            headers={"Authorization": "Bearer solfoundry-admin"},
        )
        assert resp.status_code == 200
        assert resp.json()["velocity_max_prs_per_hour"] == 10

    def test_update_config_empty_body(self, client):
        resp = client.patch(
            "/api/spam/config",
            json={},
            headers={"Authorization": "Bearer solfoundry-admin"},
        )
        assert resp.status_code == 400
